package com.careeros.ratelimit;

import java.time.Duration;
import java.util.List;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.data.redis.core.script.RedisScript;
import org.springframework.stereotype.Component;

/**
 * Redis sliding-window limiter backed by a sorted set (score = epoch millis, member = unique id).
 * Fails OPEN when Redis is unavailable so an outage cannot lock users out of the product.
 *
 * <p>The whole decision is <b>one Lua script</b>, and that is the design rather than an
 * optimisation. The previous implementation issued four commands — ZREMRANGEBYSCORE,
 * ZCOUNT, ZADD, EXPIRE — as separate round trips. Two concurrent callers (production runs
 * three backend replicas behind many Tomcat threads) could both read {@code live < limit},
 * both add, and blow the configured ceiling under exactly the concurrency it exists to
 * bound. Redis evaluates a script atomically: the trim, count and add happen with no other
 * command in between, so the ceiling holds across the fleet. This is the same fix the
 * gateway's edge budget already carries ({@code RedisBudget}); here it reaches the backend.
 */
@Component
public class RedisSlidingWindowRateLimiter {

    private static final Logger log = LoggerFactory.getLogger(RedisSlidingWindowRateLimiter.class);

    /**
     * KEYS[1] bucket, ARGV[1] cutoff (now - window - 1), ARGV[2] now, ARGV[3] limit,
     * ARGV[4] unique member, ARGV[5] TTL ms. Returns 1 on admission, 0 on refusal.
     * The cutoff/now boundary preserves the old {@code count(key, windowStart, now)}
     * semantics exactly: entries with score in [windowStart, now] are live.
     */
    static final String SCRIPT = """
            redis.call('ZREMRANGEBYSCORE', KEYS[1], 0, ARGV[1])
            local live = redis.call('ZCARD', KEYS[1])
            if live >= tonumber(ARGV[3]) then
              redis.call('PEXPIRE', KEYS[1], ARGV[5])
              return 0
            end
            redis.call('ZADD', KEYS[1], ARGV[2], ARGV[4])
            redis.call('PEXPIRE', KEYS[1], ARGV[5])
            return 1
            """;

    private final StringRedisTemplate redis;
    private final RedisScript<Long> script;

    public RedisSlidingWindowRateLimiter(StringRedisTemplate redis) {
        this.redis = redis;
        this.script = new DefaultRedisScript<>(SCRIPT, Long.class);
    }

    /**
     * One atomic admission decision. Fails OPEN on a Redis outage (an outage must not lock
     * users out) — deliberately the opposite of the gateway edge, which fails closed on an
     * empty answer. Here an empty/outage answer is admitted, matching the historical
     * fail-open contract of this backend limiter.
     */
    public boolean tryAcquire(String key, int limit, Duration window) {
        long now = System.currentTimeMillis();
        long cutoff = now - window.toMillis() - 1;
        try {
            Long allowed = redis.execute(script, List.of(key),
                    String.valueOf(cutoff),
                    String.valueOf(now),
                    String.valueOf(limit),
                    now + ":" + UUID.randomUUID(),
                    String.valueOf(window.toMillis() + 5_000));
            if (allowed == null) {
                log.warn("Rate limiter script returned empty for key {}, failing open", key);
                return true;
            }
            return allowed == 1L;
        } catch (RuntimeException e) {
            log.warn("Rate limiter Redis failure, failing open for key {}: {}", key, e.toString());
            return true;
        }
    }

    /**
     * How many more acquisitions the key has left in the current window. Used by the
     * rate-limit status endpoint (16.2). This is a separate, NON-authoritative read — it
     * does not decide admissions and is not part of the atomic path. Returns the full limit
     * when Redis is unavailable, because {@link #tryAcquire} would have admitted everything.
     */
    public long remaining(String key, int limit) {
        try {
            long now = System.currentTimeMillis();
            var zset = redis.opsForZSet();
            zset.removeRangeByScore(key, 0, now - 60_000 - 1);
            Long live = zset.count(key, now - 60_000, now);
            long used = live != null ? live : 0;
            return Math.max(0, limit - used);
        } catch (RuntimeException e) {
            return limit;
        }
    }
}
