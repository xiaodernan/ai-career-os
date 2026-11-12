package com.careeros.auth.retention;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.queue.JobQueue;
import java.time.Duration;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Map;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;

/**
 * The retention sweep's tick, pinned on the behaviours that are easy to lose while the
 * class grows: the inline path is byte-for-byte today's behaviour when the queue is
 * disabled, the election is the only place a sibling gets to skip, and a Redis hiccup at
 * the tick falls open toward the work.
 */
class RetentionSchedulerTest {

    private JobQueue queue;
    private RetentionSweeper sweeper;
    private StringRedisTemplate redis;
    private ValueOperations<String, String> ops;
    private RetentionScheduler tick;

    @BeforeEach
    void setUp() {
        queue = mock(JobQueue.class);
        sweeper = mock(RetentionSweeper.class);
        redis = mock(StringRedisTemplate.class);
        ops = mock(ValueOperations.class);
        when(redis.opsForValue()).thenReturn(ops);
        tick = new RetentionScheduler(queue, sweeper, redis);
    }

    @Test
    void theLeaderKeyIsTheUtcCalendarDay() {
        String key = RetentionScheduler.leaderKey(LocalDate.parse("2026-11-13"));
        assertThat(key).isEqualTo("careeros:v1:retention:owner:2026-11-13");
        assertThat(RetentionScheduler.leaderKey(LocalDate.now(ZoneOffset.UTC)))
                .isEqualTo("careeros:v1:retention:owner:" + LocalDate.now(ZoneOffset.UTC));
    }

    @Test
    void withTheQueueDisabledEveryReplicaSweepsExactlyAsBefore() {
        when(queue.enabled()).thenReturn(false);

        tick.tick();

        verify(sweeper).sweep(org.mockito.ArgumentMatchers.any(OffsetDateTime.class));
        verify(redis, never()).opsForValue(); // no election even attempted
    }

    @Test
    void withTheElectionWonAndTheQueueAcceptingNobodyDoubleRuns() {
        when(queue.enabled()).thenReturn(true);
        when(ops.setIfAbsent(eq(RetentionScheduler.leaderKey(LocalDate.now(ZoneOffset.UTC))),
                eq("1"), eq(Duration.ofDays(1)))).thenReturn(true);
        when(queue.enqueue(eq(RetentionSweepHandler.KIND), eq(Map.of()))).thenReturn(true);

        tick.tick();

        verify(queue).enqueue(RetentionSweepHandler.KIND, Map.of());
        verify(sweeper, never()).sweep(org.mockito.ArgumentMatchers.any());
    }

    @Test
    void withTheElectionWonAndTheQueueRefusingTheLeaderRunsInlineAlone() {
        when(queue.enabled()).thenReturn(true);
        when(ops.setIfAbsent(eq(RetentionScheduler.leaderKey(LocalDate.now(ZoneOffset.UTC))),
                eq("1"), eq(Duration.ofDays(1)))).thenReturn(true);
        when(queue.enqueue(eq(RetentionSweepHandler.KIND), eq(Map.of()))).thenReturn(false);

        tick.tick();

        verify(sweeper).sweep(org.mockito.ArgumentMatchers.any(OffsetDateTime.class));
    }

    @Test
    void withTheElectionLostTheSiblingSweepsNothingAndEnqueuesNothing() {
        when(queue.enabled()).thenReturn(true);
        when(ops.setIfAbsent(eq(RetentionScheduler.leaderKey(LocalDate.now(ZoneOffset.UTC))),
                eq("1"), eq(Duration.ofDays(1)))).thenReturn(false);

        tick.tick();

        verify(sweeper, never()).sweep(org.mockito.ArgumentMatchers.any());
        verify(queue, never()).enqueue(org.mockito.ArgumentMatchers.anyString(), eq(Map.of()));
    }

    @Test
    void withTheElectionThrowingTheReplicaRunsInlineRatherThanSkipTheNight() {
        when(queue.enabled()).thenReturn(true);
        doThrow(new IllegalStateException("redis down"))
                .when(ops).setIfAbsent(org.mockito.ArgumentMatchers.anyString(),
                        org.mockito.ArgumentMatchers.anyString(),
                        org.mockito.ArgumentMatchers.any(Duration.class));

        tick.tick();

        // Fail-open toward the work: one duplicated pass is better than a skipped one.
        verify(sweeper).sweep(org.mockito.ArgumentMatchers.any(OffsetDateTime.class));
    }
}
