package com.careeros.ratelimit;

import java.time.Duration;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

/**
 * Redis sliding-window limiter backed by a sorted set (score = epoch millis, member = unique id).
 * Fails OPEN when Redis is unavailable so an outage cannot lock users out of the product.
 */
@Component
public class RedisSlidingWindowRateLimiter {

    private static final Logger log = LoggerFactory.getLogger(RedisSlidingWindowRateLimiter.class);

    private final StringRedisTemplate redis;

    public RedisSlidingWindowRateLimiter(StringRedisTemplate redis) {
        this.redis = redis;
    }

    public boolean tryAcquire(String key, int limit, Duration window) {
        long now = System.currentTimeMillis();
        long windowStart = now - window.toMillis();
        try {
            var zset = redis.opsForZSet();
            zset.removeRangeByScore(key, 0, windowStart - 1);
            Long live = zset.count(key, windowStart, now);
            if (live != null && live >= limit) {
                return false;
            }
            zset.add(key, now + ":" + UUID.randomUUID(), (double) now);
            redis.expire(key, window.plusSeconds(5));
            return true;
        } catch (RuntimeException e) {
            log.warn("Rate limiter Redis failure, failing open for key {}: {}", key, e.toString());
            return true;
        }
    }

    /**
     * How many more acquisitions the key has left in the current window. Used by the
     * rate-limit status endpoint (16.2). Returns the full limit when Redis is
     * unavailable — the fail-open branch of {@link #tryAcquire} means every request
     * would have been admitted, so "unknown remaining" is honestly "not throttled".
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
