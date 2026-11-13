package com.careeros.notification.service;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.push.service.PushDeliveryMetrics;
import com.careeros.queue.JobQueue;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;

/**
 * The minute clock a reminder rings on (roadmap 35.1) and writes its letter on (41.1).
 *
 * <p>What is pinned is the window, because the window is the whole design. The first tick after a
 * boot reaches back one minute, so the minute the process started in is not lost; a completed
 * tick moves the window's left edge to the moment it read, so the next tick asks for exactly the
 * elapsed span; and a tick that failed moves nothing, so the next one asks for the same span
 * again rather than letting a reminder disappear into a window nobody read.
 *
 * <p>The two halves share a window but not a failure: one throwing does not skip the other, and
 * either one throwing holds the window where it was. The heartbeat is the second claim: it moves
 * at the end of every completed tick -- with or without a reminder to ring or letter to write --
 * and does not move for a tick that threw, because a pass that never read its audience is not
 * evidence that the clock is alive.
 *
 * <p>The fleet semantics are the third claim: one node rings any minute, granted by the short
 * lease when the queue is enabled; a losing sibling rings nothing and moves nothing; a Redis
 * failure closes the clock — better silent than duplicated pings to real phones.
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
    private ReminderMailService mail;
    private PushDeliveryMetrics metrics;
    private JobQueue queue;
    private StringRedisTemplate redis;
    private ValueOperations<String, String> ops;
    private ReminderScheduler scheduler;

    @BeforeEach
    void setUp() {
        push = mock(NotificationPushService.class);
        mail = mock(ReminderMailService.class);
        metrics = mock(PushDeliveryMetrics.class);
        queue = mock(JobQueue.class);
        when(queue.enabled()).thenReturn(false);
        redis = mock(StringRedisTemplate.class);
        ops = mock(ValueOperations.class);
        when(redis.opsForValue()).thenReturn(ops);
        scheduler = new ReminderScheduler(push, mail, metrics, queue, redis, clock);
        when(push.pushDue(any(), any())).thenReturn(0);
        when(mail.mailDue(any(), any())).thenReturn(0);
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
    void withTheQueueEnabledAndTheLeaseWonTheMinuteRunsAndTheHeartbeatMoves() {
        when(queue.enabled()).thenReturn(true);
        when(ops.setIfAbsent(eq("careeros:v1:lease:reminders-clock"), eq("1"),
                eq(Duration.ofSeconds(90)))).thenReturn(true);
        advance(60);

        scheduler.tick();

        verify(push).pushDue(FIRST_START, OffsetDateTime.parse("2026-10-30T10:01:00Z"));
        verify(metrics).recordDueTick(OffsetDateTime.parse("2026-10-30T10:01:00Z"));
    }

    @Test
    void withTheQueueEnabledAndTheLeaseLostTheClockIsSilent() {
        when(queue.enabled()).thenReturn(true);
        when(ops.setIfAbsent(eq("careeros:v1:lease:reminders-clock"), eq("1"),
                eq(Duration.ofSeconds(90)))).thenReturn(false);
        advance(60);

        scheduler.tick();

        verify(push, never()).pushDue(any(), any());
        verify(mail, never()).mailDue(any(), any());
        verify(metrics, never()).recordDueTick(any());
    }

    @Test
    void withTheQueueEnabledAndRedisDownTheClockIsClosedNotDuplicated() {
        when(queue.enabled()).thenReturn(true);
        doThrow(new IllegalStateException("redis down"))
                .when(ops).setIfAbsent(anyString(), eq("1"), eq(Duration.ofSeconds(90)));
        advance(60);

        scheduler.tick();

        verify(push, never()).pushDue(any(), any());
        verify(mail, never()).mailDue(any(), any());
        verify(metrics, never()).recordDueTick(any());
    }

    @Test
    void withTheQueueEnabledAndTheLeaseLostThenWonTheNextWonTickCoversEverythingSinceTheLastRead() {
        when(queue.enabled()).thenReturn(true);
        when(ops.setIfAbsent(org.mockito.ArgumentMatchers.anyString(), eq("1"),
                eq(Duration.ofSeconds(90)))).thenReturn(false, true);

        advance(60);
        scheduler.tick(); // lost: the fleet leader rings this minute; this node stands down
        advance(60);
        scheduler.tick(); // won: a takeover; the window reaches back to the last read

        // The window carried nothing across the lost minute on purpose: the episodes
        // the leader rang are latched inside the service, so asking again costs reads,
        // not re-pings. Nothing is lost: an episode never rung by the leader is rung now.
        verify(push).pushDue(FIRST_START, OffsetDateTime.parse("2026-10-30T10:02:00Z"));
    }
}
