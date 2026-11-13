package com.careeros.report.service;

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
 * The weekly letter's two clocks, enabled mode (Epic 169): the lease picks exactly one
 * replica per concern per UTC day; a refused enqueue runs inline; a lease error
 * fails open toward the work. The handler tests carry the clock's own behaviour.
 */
class WeeklyDigestSchedulerTest {

    private JobQueue queue;
    private WeeklyDigestComposeHandler compose;
    private WeeklyDigestRetryHandler retry;
    private StringRedisTemplate redis;
    private ValueOperations<String, String> ops;
    private WeeklyDigestScheduler scheduler;

    @BeforeEach
    void setUp() {
        queue = mock(JobQueue.class);
        compose = mock(WeeklyDigestComposeHandler.class);
        retry = mock(WeeklyDigestRetryHandler.class);
        redis = mock(StringRedisTemplate.class);
        ops = mock(ValueOperations.class);
        when(redis.opsForValue()).thenReturn(ops);
        scheduler = new WeeklyDigestScheduler(queue, compose, retry,
                new RedisDayLease(redis));
    }

    private String leaseKey(String concern) {
        return RedisDayLease.keyOf(concern, LocalDate.now(ZoneOffset.UTC));
    }

    @Test
    void withTheQueueDisabledTheMondayClockRunsInlineOnEveryReplica() {
        when(queue.enabled()).thenReturn(false);

        scheduler.publish();

        verify(compose).handle(Map.of());
        verify(redis, never()).opsForValue();
    }

    @Test
    void withTheQueueEnabledAndTheComposeLeaseWonTheFleetEnqueuesOnce() {
        when(queue.enabled()).thenReturn(true);
        when(ops.setIfAbsent(eq(leaseKey("digest.compose")), eq("1"),
                eq(java.time.Duration.ofDays(1)))).thenReturn(true);
        when(queue.enqueue(eq(WeeklyDigestComposeHandler.KIND), eq(Map.of()))).thenReturn(true);

        scheduler.publish();

        verify(queue).enqueue(WeeklyDigestComposeHandler.KIND, Map.of());
        verify(compose, never()).handle(Map.of());
    }

    @Test
    void withTheComposeLeaseWonAndTheQueueRefusingTheLeaderRunsInlineAlone() {
        when(queue.enabled()).thenReturn(true);
        when(ops.setIfAbsent(eq(leaseKey("digest.compose")), eq("1"),
                eq(java.time.Duration.ofDays(1)))).thenReturn(true);
        when(queue.enqueue(eq(WeeklyDigestComposeHandler.KIND), eq(Map.of()))).thenReturn(false);

        scheduler.publish();

        verify(compose).handle(Map.of());
    }

    @Test
    void withTheComposeLeaseLostSiblingsRunNothingAndEnqueueNothing() {
        when(queue.enabled()).thenReturn(true);
        when(ops.setIfAbsent(eq(leaseKey("digest.compose")), eq("1"),
                eq(java.time.Duration.ofDays(1)))).thenReturn(false);

        scheduler.publish();

        verify(compose, never()).handle(Map.of());
        verify(queue, never()).enqueue(eq(WeeklyDigestComposeHandler.KIND), eq(Map.of()));
    }

    @Test
    void withTheComposeLeaseThrowingTheReplicaRunsInlineRatherThanSkipTheWeek() {
        when(queue.enabled()).thenReturn(true);
        doThrow(new IllegalStateException("redis down"))
                .when(ops).setIfAbsent(eq(leaseKey("digest.compose")), eq("1"),
                        eq(java.time.Duration.ofDays(1)));

        scheduler.publish();

        verify(compose).handle(Map.of()); // fail-open toward the work
    }

    @Test
    void theRetryClockGetsItsOwnLeaseSoTheTwoFireIndependently() {
        when(queue.enabled()).thenReturn(true);
        when(ops.setIfAbsent(eq(leaseKey("digest.retry")), eq("1"),
                eq(java.time.Duration.ofDays(1)))).thenReturn(true);
        when(queue.enqueue(eq(WeeklyDigestRetryHandler.KIND), eq(Map.of()))).thenReturn(true);

        scheduler.retry();

        verify(queue).enqueue(WeeklyDigestRetryHandler.KIND, Map.of());
        verify(retry, never()).handle(Map.of());
    }
}
