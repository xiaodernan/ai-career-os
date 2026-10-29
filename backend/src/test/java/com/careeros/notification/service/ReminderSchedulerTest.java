package com.careeros.notification.service;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.push.service.PushDeliveryMetrics;
import java.time.Clock;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/**
 * The minute clock a reminder rings on (roadmap 35.1).
 *
 * <p>What is pinned is the window, because the window is the whole design. The first tick after a
 * boot reaches back one minute, so the minute the process started in is not lost; a completed
 * tick moves the window's left edge to the moment it read, so the next tick asks for exactly the
 * elapsed span; and a tick that failed moves nothing, so the next one asks for the same span
 * again rather than letting a reminder disappear into a window nobody read.
 *
 * <p>The heartbeat is the second claim: it moves at the end of every completed tick -- with or
 * without a reminder to ring -- and does not move for a tick that threw, because a pass that
 * never read its audience is not evidence that the clock is alive.
 */
class ReminderSchedulerTest {

    private static final Instant BOOT = Instant.parse("2026-10-30T10:00:00Z");
    private static final OffsetDateTime FIRST_START = OffsetDateTime.parse("2026-10-30T09:59:00Z");

    private final AtomicReference<Instant> instant = new AtomicReference<>(BOOT);
    private final Clock clock = new Clock() {
        @Override
        public ZoneId getZone() {
            return ZoneOffset.UTC;
        }

        @Override
        public Clock withZone(ZoneId zone) {
            return this;
        }

        @Override
        public Instant instant() {
            return instant.get();
        }
    };

    private NotificationPushService push;
    private PushDeliveryMetrics metrics;
    private ReminderScheduler scheduler;

    @BeforeEach
    void setUp() {
        push = mock(NotificationPushService.class);
        metrics = mock(PushDeliveryMetrics.class);
        scheduler = new ReminderScheduler(push, metrics, clock);
        when(push.pushDue(any(), any())).thenReturn(0);
    }

    private void advance(long seconds) {
        instant.set(instant.get().plusSeconds(seconds));
    }

    @Test
    void theFirstTickReachesBackOneMinuteSoTheBootMinuteIsNotLost() {
        advance(60);

        scheduler.tick();

        verify(push).pushDue(FIRST_START, OffsetDateTime.parse("2026-10-30T10:01:00Z"));
    }

    @Test
    void aCompletedTickMovesTheWindowSoTheNextTickAsksForTheElapsedSpanOnly() {
        advance(60);
        scheduler.tick();
        advance(60);

        scheduler.tick();

        verify(push).pushDue(OffsetDateTime.parse("2026-10-30T10:01:00Z"),
                OffsetDateTime.parse("2026-10-30T10:02:00Z"));
    }

    @Test
    void aTickThatThrewMovesNothingSoTheSameSpanIsAskedAgain() {
        advance(60);
        when(push.pushDue(any(), any())).thenThrow(new IllegalStateException("database down"));
        scheduler.tick();
        advance(60);

        scheduler.tick();

        verify(push).pushDue(FIRST_START, OffsetDateTime.parse("2026-10-30T10:02:00Z"));
    }

    @Test
    void aCompletedTickMovesTheHeartbeatEvenWhenNothingWasDue() {
        advance(60);

        scheduler.tick();

        verify(metrics).recordDueTick(OffsetDateTime.parse("2026-10-30T10:01:00Z"));
    }

    @Test
    void aTickThatThrewLeavesTheHeartbeatWhereItWas() {
        when(push.pushDue(any(), any())).thenThrow(new IllegalStateException("database down"));

        scheduler.tick();

        verify(metrics, never()).recordDueTick(any());
    }
}
