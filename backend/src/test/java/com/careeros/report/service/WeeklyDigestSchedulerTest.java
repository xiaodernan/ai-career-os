package com.careeros.report.service;

import static org.assertj.core.api.Assertions.assertThatCode;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.time.LocalDate;
import java.time.ZoneOffset;
import org.junit.jupiter.api.Test;

/**
 * The weekly letter's two clocks (roadmap 19.4, 21.3).
 *
 * <p>The Monday night writes the week that just ended, not the one starting: by Monday
 * morning the previous week's rows can no longer change, so its letter is final. The morning
 * retry is the other clock: it asks the service for the refused letters again. A sweep or a
 * retry that throws is logged, never rethrown -- a scheduler thread that dies costs every
 * future night. A completed compose moves the heartbeat (roadmap 22.4); a failed compose and
 * a retry do not, because the heartbeat answers whether the Monday clock fired, not whether a
 * letter left.
 */
class WeeklyDigestSchedulerTest {

    @Test
    void theMondayRunWritesTheWeekThatJustEndedAndHeartbeats() {
        WeeklyDigestService digests = mock(WeeklyDigestService.class);
        WeeklyDigestDeliveryMetrics metrics = mock(WeeklyDigestDeliveryMetrics.class);
        new WeeklyDigestScheduler(digests, metrics).publish();

        LocalDate lastMonday = WeeklyDigestService
                .weekStartOf(LocalDate.now(ZoneOffset.UTC)).minusWeeks(1);
        verify(digests).composeWeek(lastMonday);
        verify(metrics).recordSweep(any());
    }

    @Test
    void aFailedSweepIsLoggedRatherThanThrownAndWritesNoHeartbeat() {
        WeeklyDigestService digests = mock(WeeklyDigestService.class);
        WeeklyDigestDeliveryMetrics metrics = mock(WeeklyDigestDeliveryMetrics.class);
        when(digests.composeWeek(any())).thenThrow(new IllegalStateException("no audience"));

        assertThatCode(() -> new WeeklyDigestScheduler(digests, metrics).publish())
                .doesNotThrowAnyException();
        verify(metrics, never()).recordSweep(any());
    }

    @Test
    void theMorningRetryAsksTheServiceForTheRefusedLettersAgainAndMovesNoHeartbeat() {
        WeeklyDigestService digests = mock(WeeklyDigestService.class);
        WeeklyDigestDeliveryMetrics metrics = mock(WeeklyDigestDeliveryMetrics.class);
        new WeeklyDigestScheduler(digests, metrics).retry();

        verify(digests).retryUndelivered();
        verify(metrics, never()).recordSweep(any());
    }

    @Test
    void aFailedRetryIsLoggedRatherThanThrown() {
        WeeklyDigestService digests = mock(WeeklyDigestService.class);
        WeeklyDigestDeliveryMetrics metrics = mock(WeeklyDigestDeliveryMetrics.class);
        when(digests.retryUndelivered()).thenThrow(new IllegalStateException("the queue is unreadable"));

        assertThatCode(() -> new WeeklyDigestScheduler(digests, metrics).retry())
                .doesNotThrowAnyException();
    }
}
