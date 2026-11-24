package com.careeros.ratelimit;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;

import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.RedisScript;

/**
 * Epic 439 — a high-concurrency pass over the limiter's admission path, in process.
 *
 * The shipped limiter's decision is one Lua script, so Redis itself makes it atomic;
 * this test models that atomicity with a single lock around the same four operations
 * the script performs. Two hundred callers released together must get exactly the
 * configured number of admissions — no more (the race the script exists to close)
 * and no fewer (a limiter that refuses everyone is not a limiter). It runs with no
 * Redis, no Docker and no model: the fake executes the algorithm the script declares.
 */
class RedisSlidingWindowConcurrencyTest {

    private static final int CALLERS = 200;
    private static final int LIMIT = 25;

    @Test
    void twoHundredSimultaneousCallersGetExactlyTheCeiling() throws Exception {
        AtomicScriptRedis redis = new AtomicScriptRedis();
        RedisSlidingWindowRateLimiter limiter = new RedisSlidingWindowRateLimiter(redis);
        CountDownLatch start = new CountDownLatch(1);
        AtomicInteger admitted = new AtomicInteger();
        ExecutorService pool = Executors.newFixedThreadPool(16);
        try {
            List<Future<?>> futures = new java.util.ArrayList<>();
            for (int i = 0; i < CALLERS; i++) {
                futures.add(pool.submit(() -> {
                    start.await();
                    if (limiter.tryAcquire("rl:siege:key", LIMIT, Duration.ofMinutes(1))) {
                        admitted.incrementAndGet();
                    }
                    return null;
                }));
            }
            start.countDown();
            for (Future<?> future : futures) {
                future.get(30, TimeUnit.SECONDS);
            }
        } finally {
            pool.shutdownNow();
        }
        assertThat(admitted.get())
                .as("a sliding window must admit exactly its ceiling, never the whole crowd")
                .isEqualTo(LIMIT);
        assertThat(redis.decisions.get()).isEqualTo(CALLERS);
    }

    @Test
    void theWindowFreesItsSeatsWhenTheClockMovesPastIt() {
        AtomicScriptRedis redis = new AtomicScriptRedis();
        RedisSlidingWindowRateLimiter limiter = new RedisSlidingWindowRateLimiter(redis);
        for (int i = 0; i < LIMIT; i++) {
            assertThat(limiter.tryAcquire("rl:clock", LIMIT, Duration.ofMinutes(1))).isTrue();
        }
        assertThat(limiter.tryAcquire("rl:clock", LIMIT, Duration.ofMinutes(1))).isFalse();
        // The fake's clock is explicit; real Redis scores are epoch millis and expire the
        // same way. Move past the window and the same key admits a fresh batch.
        redis.advance(Duration.ofMinutes(2));
        assertThat(limiter.tryAcquire("rl:clock", LIMIT, Duration.ofMinutes(1))).isTrue();
    }

    /** The source the fake models, so a rewrite of the script cannot drift unnoticed. */
    @Test
    void theFakeStillModelsTheScriptTheLimiterShips() {
        String script = RedisSlidingWindowRateLimiter.SCRIPT;
        assertThat(script).contains("ZREMRANGEBYSCORE", "ZCARD", "ZADD", "PEXPIRE");
        assertThat(script).contains("live >= tonumber(ARGV[3])");
    }

    /**
     * A fake template whose execute() is atomic in exactly the way Redis script execution
     * is: trim, count, add and expiry happen under one lock, never between two callers.
     * Its clock is injectable so the window test can move time without sleeping.
     */
    static class AtomicScriptRedis extends StringRedisTemplate {
        // A ZSET is member -> score; counting distinct scores would silently admit
        // every caller that lands in the same millisecond, which is the whole point.
        private final Map<String, Map<String, Long>> buckets = new ConcurrentHashMap<>();
        private final AtomicInteger decisions = new AtomicInteger();
        private final long initialClock = System.currentTimeMillis();
        private volatile long clock = initialClock;

        AtomicScriptRedis() {
            super(mock(RedisConnectionFactory.class));
        }

        void advance(Duration amount) {
            clock += amount.toMillis();
        }

        @Override
        @SuppressWarnings("unchecked")
        public <T> T execute(RedisScript<T> script, List<String> keys, Object... args) {
            decisions.incrementAndGet();
            synchronized (buckets) {
                // The limiter reads the real system clock; shift its timestamps by the
                // fake's offset so advancing time moves both the cutoff and the score.
                long offset = clock - initialClock;
                long cutoff = Long.parseLong(args[0].toString()) + offset;
                long now = Long.parseLong(args[1].toString()) + offset;
                int limit = Integer.parseInt(args[2].toString());
                String member = args[3].toString();
                String key = keys.get(0);
                Map<String, Long> live = buckets.computeIfAbsent(key, ignored -> new ConcurrentHashMap<>());
                live.values().removeIf(score -> score <= cutoff);
                if (live.size() >= limit) {
                    return (T) Long.valueOf(0L);
                }
                live.put(member, now);
                return (T) Long.valueOf(1L);
            }
        }
    }
}
