package com.careeros.ratelimit;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicIntegerArray;
import org.junit.jupiter.api.Test;

/**
 * Epic 460 — a distributed burst, not a single loud caller (Block XI).
 *
 * <p>The credential-stuffing gate answers one source hammering the door; the sliding-window
 * tests answer one key under concurrent callers. A botnet is the other shape: many distinct
 * sources, each inside its own ceiling, arriving at once. If the limiter keyed anything but
 * the caller's identity — a global counter, a shared clock bucket, a lock held across keys —
 * one crowd would silently consume another's budget and a quiet source would be refused
 * before it had tried.
 *
 * <p>This drives the limiter's own atomic path with the same fake script the other gates use:
 * no Redis, no socket, no Docker, no live API. The claim is per-key isolation under load,
 * measured as exactly the ceiling admitted for every source and a full refusal on the next
 * attempt at each, while a source that never appeared still has its whole budget.
 */
class DistributedBurstIsolationTest {

    private static final int SOURCES = 120;
    private static final int ATTEMPTS_PER_SOURCE = 20;
    private static final int THREADS = 16;
    private static final int LIMIT = 10;
    private static final Duration WINDOW = Duration.ofMinutes(1);

    @Test
    void aCrowdOfDistinctSourcesEachGetsItsOwnCeiling() throws Exception {
        RedisSlidingWindowConcurrencyTest.AtomicScriptRedis redis =
                new RedisSlidingWindowConcurrencyTest.AtomicScriptRedis();
        RedisSlidingWindowRateLimiter limiter = new RedisSlidingWindowRateLimiter(redis);
        AtomicIntegerArray admitted = new AtomicIntegerArray(SOURCES);
        AtomicIntegerArray refused = new AtomicIntegerArray(SOURCES);
        AtomicIntegerArray errors = new AtomicIntegerArray(SOURCES);
        CountDownLatch start = new CountDownLatch(1);

        ExecutorService pool = Executors.newFixedThreadPool(THREADS);
        try {
            List<Future<?>> futures = new ArrayList<>();
            for (int source = 0; source < SOURCES; source += 1) {
                final int index = source;
                String key = key(index);
                futures.add(pool.submit(() -> {
                    start.await();
                    for (int attempt = 0; attempt < ATTEMPTS_PER_SOURCE; attempt += 1) {
                        try {
                            if (limiter.tryAcquire(key, LIMIT, WINDOW)) admitted.incrementAndGet(index);
                            else refused.incrementAndGet(index);
                        } catch (RuntimeException e) {
                            errors.incrementAndGet(index);
                        }
                    }
                    return null;
                }));
            }
            start.countDown();
            for (Future<?> future : futures) future.get(60, TimeUnit.SECONDS);
        } finally {
            pool.shutdownNow();
        }

        int totalAdmitted = 0;
        for (int source = 0; source < SOURCES; source += 1) {
            assertThat(errors.get(source)).as("source %s must never raise", source).isZero();
            assertThat(admitted.get(source)).as("source %s's own ceiling", source).isEqualTo(LIMIT);
            assertThat(refused.get(source))
                    .as("source %s's surplus is refused, not borrowed from another key", source)
                    .isEqualTo(ATTEMPTS_PER_SOURCE - LIMIT);
            assertThat(limiter.tryAcquire(key(source), LIMIT, WINDOW))
                    .as("source %s is at its ceiling after the burst", source)
                    .isFalse();
            totalAdmitted += admitted.get(source);
        }
        assertThat(totalAdmitted).isEqualTo(SOURCES * LIMIT);

        // A source that never took part has not spent any other caller's budget.
        String quiet = key(SOURCES);
        assertThat(limiter.tryAcquire(quiet, LIMIT, WINDOW)).isTrue();
        assertThat(limiter.tryAcquire(quiet, LIMIT, WINDOW)).isTrue();
    }

    private static String key(int source) {
        return "rl:auth:" + (source >= 100 ? "" : source >= 10 ? "0" : "00") + source;
    }
}
