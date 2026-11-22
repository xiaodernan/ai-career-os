package com.careeros.health;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doReturn;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.ai.AiServiceClient;
import com.careeros.storage.StorageService;
import java.sql.Connection;
import java.time.Duration;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import javax.sql.DataSource;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.data.redis.core.RedisCallback;
import org.springframework.data.redis.core.RedisTemplate;

/**
 * Who pays for the probes, and how stale an answer may be (Epics 314 and 415).
 *
 * <p>The readiness report used to be recomputed on every call; a 100-way dashboard fan-out
 * turned into 400 database connections and everyone waited. Epic 314 answered that with a
 * two-second cache, and the cache held a claim nobody checked: a caller was answered with
 * the last probe's verdict rather than with the deployment's state, so a dependency that
 * went down stayed invisible for two seconds on the one route whose whole job is naming
 * which half is down. The queue's IT asserted exactly that invisibility for three ledger
 * rows before anyone read the failure as behaviour instead of environment.
 *
 * <p>Coalescing keeps the protection the burst actually needs -- the stampede is concurrent,
 * not sequential -- and gives up no freshness to it: callers that arrive while a probe set is
 * running join that set, and a caller that arrives after it finished asks again. These tests
 * pin both halves, so neither the stampede nor the stale verdict can come back alone.
 */
class HealthServiceBurstTest {

    private DataSource dataSource;
    private Connection connection;
    private RedisTemplate<String, Object> redis;
    private StorageService storage;
    private AiServiceClient ai;

    @BeforeEach
    void setUp() throws Exception {
        dataSource = mock(DataSource.class);
        connection = mock(Connection.class);
        when(dataSource.getConnection()).thenReturn(connection);
        when(connection.isValid(2)).thenReturn(true);

        redis = mock(RedisTemplate.class);
        doReturn("PONG").when(redis).execute(any(RedisCallback.class), eq(true));

        storage = mock(StorageService.class);
        when(storage.available()).thenReturn(true);

        ai = mock(AiServiceClient.class);
        when(ai.healthy()).thenReturn(true);
        when(ai.healthyNodes()).thenReturn(Map.of("http://ai-service:8000", true));
    }

    private HealthService service() {
        return new HealthService(dataSource, redis, Optional.of(storage), ai,
                Duration.ofSeconds(2));
    }

    /**
     * A probe set the test orchestrates has to outlive the orchestration: the leader's own
     * budget would otherwise report the stalled probe as false before the test releases it.
     */
    private HealthService slowService() {
        return new HealthService(dataSource, redis, Optional.of(storage), ai,
                Duration.ofSeconds(10));
    }

    /**
     * Parked in {@code done.await} is the one state that proves a caller joined the set in
     * flight rather than starting its own; releasing the leader before that would let a late
     * caller lead a second set and make the probe count a coin flip.
     */
    private static void awaitPark(Thread... waiters) throws InterruptedException {
        long until = System.nanoTime() + TimeUnit.SECONDS.toNanos(5);
        while (System.nanoTime() < until) {
            boolean allParked = true;
            for (Thread waiter : waiters) {
                Thread.State state = waiter.getState();
                allParked &= state == Thread.State.WAITING || state == Thread.State.TIMED_WAITING;
            }
            if (allParked) {
                return;
            }
            Thread.sleep(5);
        }
        throw new IllegalStateException("a waiter never reached its shared probe set");
    }

    @Test
    void aBurstJoinedToOneProbeSetPaysForOneProbeSet() throws Exception {
        HealthService service = slowService();
        CountDownLatch probing = new CountDownLatch(1);
        CountDownLatch release = new CountDownLatch(1);
        when(storage.available()).thenAnswer(call -> {
            probing.countDown();
            release.await();
            return true;
        });

        Thread leader = new Thread(service::reportCached, "burst-leader");
        leader.start();
        assertThat(probing.await(5, TimeUnit.SECONDS)).isTrue();

        Map<String, Object>[] answers = newMapArray(3);
        Thread[] waiters = new Thread[3];
        for (int i = 0; i < waiters.length; i++) {
            int slot = i;
            waiters[i] = new Thread(() -> answers[slot] = service.reportCached(), "burst-waiter-" + i);
            waiters[i].start();
        }
        awaitPark(waiters);
        release.countDown();
        for (Thread waiter : waiters) {
            waiter.join(5_000);
        }
        leader.join(5_000);

        verify(storage, times(1)).available();
        for (Map<String, Object> answer : answers) {
            assertThat(answer).containsEntry("status", "ok").containsEntry("storage", true);
        }
    }

    @Test
    void aDependencyThatWentDownBetweenCallsIsReportedByTheNextCall() throws Exception {
        HealthService service = service();

        assertThat(service.reportCached().get("status")).isEqualTo("ok");
        when(storage.available()).thenReturn(false);

        assertThat(service.reportCached())
                .containsEntry("status", "degraded")
                .containsEntry("storage", false);
        verify(storage, times(2)).available();
    }

    @Test
    void everyCallerGetsItsOwnCopyOfTheSharedReport() throws Exception {
        HealthService service = service();

        Map<String, Object> first = service.reportCached();
        first.put("status", "corrupted");

        assertThat(service.reportCached().get("status")).isEqualTo("ok");
    }

    @Test
    void aDegradedVerdictIsSharedWithTheBurstNotHiddenFromIt() throws Exception {
        HealthService service = slowService();
        CountDownLatch probing = new CountDownLatch(1);
        CountDownLatch release = new CountDownLatch(1);
        when(storage.available()).thenAnswer(call -> {
            probing.countDown();
            release.await();
            return false;
        });

        Map<String, Object>[] answers = newMapArray(2);
        Thread leader = new Thread(() -> answers[0] = service.reportCached(), "degraded-leader");
        leader.start();
        assertThat(probing.await(5, TimeUnit.SECONDS)).isTrue();
        Thread waiter = new Thread(() -> answers[1] = service.reportCached(), "degraded-waiter");
        waiter.start();
        awaitPark(waiter);
        release.countDown();
        waiter.join(5_000);
        leader.join(5_000);

        // The burst shares the bad news rather than each caller learning it separately, and the
        // cache's old failure mode -- an ok verdict served to a deployment that has lost a half --
        // has no room to appear here: one probe set, one verdict, both callers.
        verify(storage, times(1)).available();
        assertThat(answers[0]).containsEntry("status", "degraded").containsEntry("storage", false);
        assertThat(answers[1]).containsEntry("status", "degraded").containsEntry("storage", false);
    }

    @Test
    void aWaiterInterruptedOutOfItsProbeSetStillAnswers() throws Exception {
        HealthService service = new HealthService(dataSource, redis, Optional.of(storage), ai,
                Duration.ofMillis(150));
        CountDownLatch probing = new CountDownLatch(1);
        CountDownLatch release = new CountDownLatch(1);
        AtomicInteger probes = new AtomicInteger();
        // Only the leader's probe stalls: a waiter that falls back to its own report must be
        // able to finish it, or the test measures a second hang instead of the fallback.
        when(storage.available()).thenAnswer(call -> {
            if (probes.incrementAndGet() == 1) {
                probing.countDown();
                release.await();
            }
            return true;
        });

        Thread leader = new Thread(service::reportCached, "interrupt-leader");
        leader.start();
        assertThat(probing.await(5, TimeUnit.SECONDS)).isTrue();

        boolean[] answered = {false};
        boolean[] interruptedFlag = {false};
        Thread waiter = new Thread(() -> {
            service.reportCached();
            answered[0] = true;
            interruptedFlag[0] = Thread.currentThread().isInterrupted();
        }, "interrupt-waiter");
        waiter.start();
        awaitPark(waiter);
        waiter.interrupt();
        waiter.join(5_000);
        release.countDown();
        leader.join(5_000);

        assertThat(answered[0]).isTrue();
        // The wait is not the caller's stop to swallow: the flag travels on (awaitValue's rule).
        assertThat(interruptedFlag[0]).isTrue();
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object>[] newMapArray(int size) {
        return new Map[size];
    }

    @Test
    void livenessAnswersOkAndAsksNothing() {
        HealthService service = service();

        Map<String, Object> live = service.liveness();

        assertThat(live.get("status")).isEqualTo("ok");
        assertThat(live.get("kind")).isEqualTo("liveness");
        assertThat(((Number) live.get("uptimeMs")).longValue()).isGreaterThanOrEqualTo(0);
        verify(storage, never()).available();
        verify(ai, never()).healthyNodes();
    }
}
