package com.careeros.report.service;

import static org.assertj.core.api.Assertions.assertThatCode;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.time.LocalDate;
import java.time.ZoneOffset;
import org.junit.jupiter.api.Test;

/**
 * The Monday clock (roadmap 19.4).
 *
 * <p>The night writes the week that just ended, not the one starting: by Monday morning the
 * previous week's rows can no longer change, so its letter is final. A sweep that throws is
 * logged, never rethrown -- a scheduler thread that dies costs every future night.
 */
class WeeklyDigestSchedulerTest {

    @Test
    void theMondayRunWritesTheWeekThatJustEnded() {
        WeeklyDigestService digests = mock(WeeklyDigestService.class);
        new WeeklyDigestScheduler(digests).publish();

        LocalDate lastMonday = WeeklyDigestService
                .weekStartOf(LocalDate.now(ZoneOffset.UTC)).minusWeeks(1);
        verify(digests).composeWeek(lastMonday);
    }

    @Test
    void aFailedSweepIsLoggedRatherThanThrown() {
        WeeklyDigestService digests = mock(WeeklyDigestService.class);
        when(digests.composeWeek(any())).thenThrow(new IllegalStateException("no audience"));

        assertThatCode(() -> new WeeklyDigestScheduler(digests).publish())
                .doesNotThrowAnyException();
    }
}
