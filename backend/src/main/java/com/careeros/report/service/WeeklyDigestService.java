package com.careeros.report.service;

import com.careeros.application.repository.ApplicationRepository;
import com.careeros.auth.entity.User;
import com.careeros.auth.repository.UserRepository;
import com.careeros.common.Paging;
import com.careeros.mail.service.MailList;
import com.careeros.mail.service.MailPreferenceService;
import com.careeros.report.dto.WeeklyDigestDtos.WeeklyDigestDto;
import com.careeros.report.entity.WeeklyDigest;
import com.careeros.report.repository.WeeklyDigestRepository;
import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.temporal.TemporalAdjusters;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * The weekly letter (roadmap 19.4): the 15.3 digest composed on a cadence and kept.
 *
 * <p>The dashboard's digest is computed when someone opens the page; this one is composed when
 * the night runs and stored, so the week's signals survive the week and are readable without
 * the engine. The payload is the engine's answer verbatim -- the same shape the analysis page
 * already reads -- because a second composition of the same numbers would be a second answer
 * to the same question.
 *
 * <p>One row per user per week, refreshed in place: re-composing a week that already has a
 * letter replaces it rather than filing a second one. The scheduler writes the week that just
 * ended, when it can no longer change; the manual route writes the current week, as it stands.
 *
 * <p>The letter is composed without a browser, but not without a reader (roadmap 21.4): the
 * account keeps the language its switch chose, and that is the language the engine is asked
 * for its signals in and the language the mail chrome is written in. The language is frozen
 * on the row beside the payload it wrote, so a retry days later mails the same letter rather
 * than chrome that disagrees with its own sentences.
 *
 * <p>On the sweeper's path the letter is also mailed (roadmap 21.2): the row is written first
 * and handed to the transport second, so a refused letter is a stored letter with an error on
 * it, never a week that vanished. {@code delivered_at} is the latch as much as the receipt --
 * a week recomposed after a successful send is not mailed a second time.
 *
 * <p>A refused letter is not abandoned (roadmap 21.3): a daily retry clock asks for the
 * undelivered letters that were actually attempted and tries again, oldest week first, until
 * {@link #MAX_DELIVERY_ATTEMPTS} is reached. Only attempted letters are retried, because zero
 * attempts is the dashboard's compose and that route's promise is that composing is not
 * sending.
 */
@Service
public class WeeklyDigestService {

    private static final Logger log = LoggerFactory.getLogger(WeeklyDigestService.class);

    /** The letter is about the last seven days, so "quiet" means a week without movement. */
    static final int WINDOW_DAYS = 7;
    /** How many weeks the analysis page can walk back before the list becomes a wall. */
    static final int HISTORY_LIMIT = 12;
    /** The transport's refusal is kept for a reader, not an incident report; the column holds 500. */
    static final int DELIVERY_ERROR_LIMIT = 500;
    /** After this many refusals the letter is left on its row with its error, not retried again. */
    static final int MAX_DELIVERY_ATTEMPTS = 5;
    /** One retry pass touches at most this many letters; the clock runs daily, so it catches up. */
    static final int RETRY_BATCH = 100;

    private final WeeklyDigestRepository digests;
    private final ApplicationRepository applications;
    private final AnalysisService analysis;
    private final UserRepository users;
    private final WeeklyDigestMailer mailer;
    private final WeeklyDigestDeliveryMetrics metrics;
    private final MailPreferenceService preferences;

    public WeeklyDigestService(WeeklyDigestRepository digests, ApplicationRepository applications,
            AnalysisService analysis, UserRepository users, WeeklyDigestMailer mailer,
            WeeklyDigestDeliveryMetrics metrics, MailPreferenceService preferences) {
        this.digests = digests;
        this.applications = applications;
        this.analysis = analysis;
        this.users = users;
        this.mailer = mailer;
        this.metrics = metrics;
        this.preferences = preferences;
    }

    /** A user's letters, newest week first. */
    @Transactional(readOnly = true)
    public List<WeeklyDigestDto> recent(UUID userId) {
        return digests.findByUserIdOrderByWeekStartDescIdDesc(userId, Paging.first(HISTORY_LIMIT))
                .stream().map(WeeklyDigestDto::of).toList();
    }

    /**
     * The current week's letter, composed now and filed in place. Composing is not sending: the
     * Monday sweep mails what it writes, so pressing the button cannot put a second copy in a
     * mailbox.
     */
    public WeeklyDigestDto composeNow(UUID userId) {
        return compose(userId, weekStartOf(LocalDate.now(ZoneOffset.UTC)));
    }

    /**
     * The scheduler's night: compose one week's letter for every account that has an
     * application to report on, and mail it. A failure is that user's letter missing and a warn
     * line, never the rest of the night: one account in a bad state must not cost every other
     * account its week. Delivery failures are recorded and already contained by {@link
     * #deliver}; a failure to even write that record is contained here. Returns how many letters
     * were written.
     */
    public int composeWeek(LocalDate weekStart) {
        int written = 0;
        for (UUID userId : applications.distinctUserIds()) {
            WeeklyDigest letter;
            try {
                letter = composeLetter(userId, weekStart);
                written++;
            } catch (RuntimeException e) {
                log.warn("weekly digest for {} could not be composed", userId, e);
                continue;
            }
            try {
                deliver(userId, letter);
            } catch (RuntimeException e) {
                log.warn("the delivery of {}'s weekly letter could not be recorded", userId, e);
            }
        }
        return written;
    }

    /**
     * The retry clock (roadmap 21.3): letters the transport refused, oldest week first, tried
     * again until {@link #MAX_DELIVERY_ATTEMPTS}. The queue is the repository's -- undelivered,
     * attempted, under the cap -- so a dashboard compose (zero attempts) is never mailed by
     * this clock, and a letter at the cap is left on its row with its last error rather than
     * retried forever. Returns how many letters this pass put in a mailbox.
     */
    public int retryUndelivered() {
        int delivered = 0;
        for (WeeklyDigest letter : digests
                .findByDeliveredAtIsNullAndDeliveryAttemptsGreaterThanAndDeliveryAttemptsLessThanOrderByWeekStartAscIdAsc(
                        0, MAX_DELIVERY_ATTEMPTS, Paging.first(RETRY_BATCH))) {
            try {
                if (deliver(letter.getUserId(), letter)) {
                    delivered++;
                }
            } catch (RuntimeException e) {
                log.warn("the retry of {}'s weekly letter could not be recorded",
                        letter.getUserId(), e);
            }
        }
        return delivered;
    }

    /**
     * One letter. The engine is asked first and the row is written afterwards: the read is the
     * expensive, failure-prone half, and a failure there must leave the previous letter -- if
     * any -- untouched rather than blanking the week.
     */
    WeeklyDigestDto compose(UUID userId, LocalDate weekStart) {
        return WeeklyDigestDto.of(composeLetter(userId, weekStart));
    }

    private WeeklyDigest composeLetter(UUID userId, LocalDate weekStart) {
        String locale = localeOf(userId);
        Map<String, Object> payload = analysis.insightDigest(userId, locale, WINDOW_DAYS);
        WeeklyDigest letter = digests.findByUserIdAndWeekStart(userId, weekStart)
                .orElseGet(() -> {
                    WeeklyDigest fresh = new WeeklyDigest();
                    fresh.setUserId(userId);
                    fresh.setWeekStart(weekStart);
                    return fresh;
                });
        letter.setWindowDays(WINDOW_DAYS);
        letter.setLocale(locale);
        letter.setPayload(payload);
        letter.setGeneratedAt(OffsetDateTime.now(ZoneOffset.UTC));
        return digests.save(letter);
    }

    /**
     * Hands one stored letter to the transport, once. The row is written first and the latch
     * second: a letter that already has a {@code delivered_at} is skipped, so re-running the
     * sweep over a week it has already mailed cannot put a second copy in the mailbox. A
     * refusal is kept on the row rather than thrown -- the sweep still has the other accounts
     * to reach, and the error is what a reader (or a later attempt) needs to know -- and the
     * attempt is counted either way, so "never tried" and "tried and refused" stay distinct.
     * An account whose row is gone is a warn line: nothing was attempted, so nothing is counted.
     *
     * <p>The scrape is told what the transport did (21.3): the outcome counter moves for every
     * attempt, and the last-delivered marker moves only on an acceptance. A refusal therefore
     * cannot make the marker claim a delivery the mailbox never received.
     *
     * <p>An account that turned the Monday letter off (23.1) is not handed to the transport at
     * all -- not by the compose sweep that just wrote its letter, and not by the retry clock
     * that would otherwise keep asking. That is not an attempt, so the attempt counter stays
     * where it was and the letter keeps its place on the reader's dashboard, which was never
     * part of the mail consent. A manual compose is likewise untouched: the reader pressed the
     * button in the app, and composing is not sending.
     *
     * @return whether this call put the letter in a mailbox; a latch hit, an opted-out account
     *     or an account row that is gone is {@code false}, because nothing was sent
     */
    boolean deliver(UUID userId, WeeklyDigest letter) {
        if (letter.getDeliveredAt() != null) {
            return false;
        }
        if (!preferences.receives(userId, MailList.WEEKLY)) {
            return false;
        }
        Optional<User> owner = users.findById(userId);
        if (owner.isEmpty()) {
            log.warn("the weekly letter for the week of {} has no account to mail ({})",
                    letter.getWeekStart(), userId);
            return false;
        }
        letter.setDeliveryAttempts(letter.getDeliveryAttempts() + 1);
        try {
            mailer.send(owner.get().getEmail(), letter);
            letter.setDeliveredAt(OffsetDateTime.now(ZoneOffset.UTC));
            letter.setDeliveryError(null);
            metrics.recordSent(letter.getDeliveredAt());
        } catch (RuntimeException e) {
            letter.setDeliveryError(describe(e));
            metrics.recordRefused();
            log.warn("the weekly letter for the week of {} could not be sent to {}",
                    letter.getWeekStart(), userId, e);
        }
        digests.save(letter);
        return letter.getDeliveredAt() != null;
    }

    private static String describe(RuntimeException e) {
        String message = e.getMessage();
        String text = message == null || message.isBlank() ? e.getClass().getSimpleName() : message;
        return text.length() <= DELIVERY_ERROR_LIMIT ? text : text.substring(0, DELIVERY_ERROR_LIMIT);
    }

    /**
     * The language the account is written to in, defaulting to the product's own when the row
     * (or its column) has none. The table constrains the column to the two languages if a value
     * is there at all; this only decides what an absent one means.
     */
    private String localeOf(UUID userId) {
        return users.findById(userId).map(User::getLocale).orElse("en");
    }

    /** The Monday of the week {@code day} falls in -- the one week-start the table accepts. */
    static LocalDate weekStartOf(LocalDate day) {
        return day.with(TemporalAdjusters.previousOrSame(DayOfWeek.MONDAY));
    }
}
