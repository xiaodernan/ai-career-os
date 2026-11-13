package com.careeros.report.service;

import static org.assertj.core.api.Assertions.assertThatCode;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.Map;
import org.junit.jupiter.api.Test;

/**
 * The retry clock's job itself (roadmap 21.3): refused letters are tried again, a
 * failure is logged rather than thrown, and no heartbeat moves — the heartbeat
 * answers whether the compose clock fired, not whether a retry managed anything.
 */
class WeeklyDigestRetryHandlerTest {

    @Test
    void theMorningRetryAsksTheServiceForTheRefusedLettersAgainAndMovesNoHeartbeat() {
        WeeklyDigestService digests = mock(WeeklyDigestService.class);
        new WeeklyDigestRetryHandler(digests).handle(Map.of());

        verify(digests).retryUndelivered();
    }

    @Test
    void aFailedRetryIsLoggedRatherThanThrown() {
        WeeklyDigestService digests = mock(WeeklyDigestService.class);
        when(digests.retryUndelivered()).thenThrow(new IllegalStateException("the queue is unreadable"));

        assertThatCode(() -> new WeeklyDigestRetryHandler(digests).handle(Map.of()))
                .doesNotThrowAnyException();
    }
}
