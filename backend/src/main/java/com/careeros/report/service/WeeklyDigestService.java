package com.careeros.report.service;

import com.careeros.application.repository.ApplicationRepository;
import com.careeros.auth.entity.User;
import com.careeros.auth.repository.UserRepository;
import com.careeros.common.Paging;
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
 * <p>The letter is composed without a reader, so the engine is asked for its default language;
 * the page prints its own translated sentences from the numbers, and the engine's own words
 * stay in the payload the mail is assembled from.
 *
 * <p>On the sweeper's path the letter is also mailed (roadmap 21.2): the row is written first
 * and handed to the transport second, so a refused letter is a stored letter with an error on
 * it, never a week that vanished. {@code delivered_at} is the latch as much as the receipt --
 * a week recomposed after a successful send is not mailed a second time.
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

    private final WeeklyDigestRepository digests;
    private final ApplicationRepository applications;
    private final AnalysisService analysis;
    private final UserRepository users;
    private final WeeklyDigestMailer mailer;

    public WeeklyDigestService(WeeklyDigestRepository digests, ApplicationRepository applications,
            AnalysisService analysis, UserRepository users, WeeklyDigestMailer mailer) {
        this.digests = digests;
        this.applications = applications;
        this.analysis = analysis;
        this.users = users;
        this.mailer = mailer;
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
     * One letter. The engine is asked first and the row is written afterwards: the read is the
     * expensive, failure-prone half, and a failure there must leave the previous letter -- if
     * any -- untouched rather than blanking the week.
     */
    WeeklyDigestDto compose(UUID userId, LocalDate weekStart) {
        return WeeklyDigestDto.of(composeLetter(userId, weekStart));
    }

    private WeeklyDigest composeLetter(UUID userId, LocalDate weekStart) {
        Map<String, Object> payload = analysis.insightDigest(userId, null, WINDOW_DAYS);
        WeeklyDigest letter = digests.findByUserIdAndWeekStart(userId, weekStart)
                .orElseGet(() -> {
                    WeeklyDigest fresh = new WeeklyDigest();
                    fresh.setUserId(userId);
                    fresh.setWeekStart(weekStart);
                    return fresh;
                });
        letter.setWindowDays(WINDOW_DAYS);
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
     */
    void deliver(UUID userId, WeeklyDigest letter) {
        if (letter.getDeliveredAt() != null) {
            return;
        }
        Optional<User> owner = users.findById(userId);
        if (owner.isEmpty()) {
            log.warn("the weekly letter for the week of {} has no account to mail ({})",
                    letter.getWeekStart(), userId);
            return;
        }
        letter.setDeliveryAttempts(letter.getDeliveryAttempts() + 1);
        try {
            mailer.send(owner.get().getEmail(), letter);
            letter.setDeliveredAt(OffsetDateTime.now(ZoneOffset.UTC));
            letter.setDeliveryError(null);
        } catch (RuntimeException e) {
            letter.setDeliveryError(describe(e));
            log.warn("the weekly letter for the week of {} could not be sent to {}",
                    letter.getWeekStart(), userId, e);
        }
        digests.save(letter);
    }

    private static String describe(RuntimeException e) {
        String message = e.getMessage();
        String text = message == null || message.isBlank() ? e.getClass().getSimpleName() : message;
        return text.length() <= DELIVERY_ERROR_LIMIT ? text : text.substring(0, DELIVERY_ERROR_LIMIT);
    }

    /** The Monday of the week {@code day} falls in -- the one week-start the table accepts. */
    static LocalDate weekStartOf(LocalDate day) {
        return day.with(TemporalAdjusters.previousOrSame(DayOfWeek.MONDAY));
    }
}
