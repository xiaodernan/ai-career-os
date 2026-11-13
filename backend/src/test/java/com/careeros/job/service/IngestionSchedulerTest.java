package com.careeros.job.service;

import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.queue.JobQueue;
import com.careeros.queue.RedisDayLease;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.Map;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;

/**
 * The ingestion sweep's clock, enabled mode (Epic 170): the lease picks exactly one
 * replica per UTC day; a refused enqueue runs inline; a lease error fails open toward
 * the work. The handler's own behavior is pinned in its class's two companion tests.
 */
class IngestionSchedulerTest {

    private JobQueue queue;
    private IngestionSweepHandler handler;
    private StringRedisTemplate redis;
    private ValueOperations<String, String> ops;
    private IngestionScheduler scheduler;

    @BeforeEach
    void setUp() {
        queue = mock(JobQueue.class);
        handler = mock(IngestionSweepHandler.class);
        redis = mock(StringRedisTemplate.class);
        ops = mock(ValueOperations.class);
        when(redis.opsForValue()).thenReturn(ops);
        scheduler = new IngestionScheduler(queue, handler, new RedisDayLease(redis));
    }

    private String leaseKey() {
        return RedisDayLease.keyOf(IngestionScheduler.CONCERN, LocalDate.now(ZoneOffset.UTC));
    }

    @Test
    void withTheQueueDisabledEveryReplicaSweepsExactlyAsBefore() {
        when(queue.enabled()).thenReturn(false);

        scheduler.sweep();

        verify(handler).handle(Map.of());
        verify(redis, never()).opsForValue();
    }

    @Test
    void withTheQueueEnabledAndTheLeaseWonTheFleetEnqueuesOnce() {
        when(queue.enabled()).thenReturn(true);
        when(ops.setIfAbsent(eq(leaseKey()), eq("1"), eq(java.time.Duration.ofDays(1)))).thenReturn(true);
        when(queue.enqueue(eq(IngestionSweepHandler.KIND), eq(Map.of()))).thenReturn(true);

        scheduler.sweep();

        verify(queue).enqueue(IngestionSweepHandler.KIND, Map.of());
        verify(handler, never()).handle(Map.of());
    }

    @Test
    void withTheLeaseWonAndTheQueueRefusingTheWinnerRunsInlineAlone() {
        when(queue.enabled()).thenReturn(true);
        when(ops.setIfAbsent(eq(leaseKey()), eq("1"), eq(java.time.Duration.ofDays(1)))).thenReturn(true);
        when(queue.enqueue(eq(IngestionSweepHandler.KIND), eq(Map.of()))).thenReturn(false);

        scheduler.sweep();

        verify(handler).handle(Map.of());
    }

    @Test
    void withTheLeaseLostSiblingsRunNothingAndEnqueueNothing() {
        when(queue.enabled()).thenReturn(true);
        when(ops.setIfAbsent(eq(leaseKey()), eq("1"), eq(java.time.Duration.ofDays(1)))).thenReturn(false);

        scheduler.sweep();

        verify(handler, never()).handle(Map.of());
        verify(queue, never()).enqueue(eq(IngestionSweepHandler.KIND), eq(Map.of()));
    }

    @Test
    void withTheLeaseThrowingTheReplicaRunsInlineRatherThanSkipTheNight() {
        when(queue.enabled()).thenReturn(true);
        doThrow(new IllegalStateException("redis down"))
                .when(ops).setIfAbsent(eq(leaseKey()), eq("1"), eq(java.time.Duration.ofDays(1)));

        scheduler.sweep();

        verify(handler).handle(Map.of());
    }
}
