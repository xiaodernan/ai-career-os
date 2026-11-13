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
 * The compose clock's job itself (roadmap 19.4), pinned where the work happens: the
 * sweep composes the week that just ended, moves the heartbeat, and never lets a bad
 * night crash the schedule thread. The election and the inline path live on the
 * scheduler; the handler is what both execute.
 */
class WeeklyDigestComposeHandlerTest {

    @Test
    void theMondayRunWritesTheWeekThatJustEndedAndHeartbeats() {
        WeeklyDigestService digests = mock(WeeklyDigestService.class);
        WeeklyDigestDeliveryMetrics metrics = mock(WeeklyDigestDeliveryMetrics.class);
        new WeeklyDigestComposeHandler(digests, metrics).handle(java.util.Map.of());

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

        assertThatCode(() -> new WeeklyDigestComposeHandler(digests, metrics).handle(java.util.Map.of()))
                .doesNotThrowAnyException();
        verify(metrics, never()).recordSweep(any());
    }
}
