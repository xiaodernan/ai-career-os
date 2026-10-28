package com.careeros.report.service;

import com.careeros.application.repository.ApplicationRepository;
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
 * stay in the payload for the email half.
 */
@Service
public class WeeklyDigestService {

    private static final Logger log = LoggerFactory.getLogger(WeeklyDigestService.class);

    /** The letter is about the last seven days, so "quiet" means a week without movement. */
    static final int WINDOW_DAYS = 7;
    /** How many weeks the analysis page can walk back before the list becomes a wall. */
    static final int HISTORY_LIMIT = 12;

    private final WeeklyDigestRepository digests;
    private final ApplicationRepository applications;
    private final AnalysisService analysis;

    public WeeklyDigestService(WeeklyDigestRepository digests, ApplicationRepository applications,
            AnalysisService analysis) {
        this.digests = digests;
        this.applications = applications;
        this.analysis = analysis;
    }

    /** A user's letters, newest week first. */
    @Transactional(readOnly = true)
    public List<WeeklyDigestDto> recent(UUID userId) {
        return digests.findByUserIdOrderByWeekStartDesc(userId, Paging.first(HISTORY_LIMIT))
                .stream().map(WeeklyDigestDto::of).toList();
    }

    /** The current week's letter, composed now and filed in place. */
    public WeeklyDigestDto composeNow(UUID userId) {
        return compose(userId, weekStartOf(LocalDate.now(ZoneOffset.UTC)));
    }

    /**
     * The scheduler's night: compose one week's letter for every account that has an
     * application to report on. A failure is that user's letter missing and a warn line, never
     * the rest of the night: one account in a bad state must not cost every other account its
     * week. Returns how many letters were written.
     */
    public int composeWeek(LocalDate weekStart) {
        int written = 0;
        for (UUID userId : applications.distinctUserIds()) {
            try {
                compose(userId, weekStart);
                written++;
            } catch (RuntimeException e) {
                log.warn("weekly digest for {} could not be composed", userId, e);
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
        return WeeklyDigestDto.of(digests.save(letter));
    }

    /** The Monday of the week {@code day} falls in -- the one week-start the table accepts. */
    static LocalDate weekStartOf(LocalDate day) {
        return day.with(TemporalAdjusters.previousOrSame(DayOfWeek.MONDAY));
    }
}
