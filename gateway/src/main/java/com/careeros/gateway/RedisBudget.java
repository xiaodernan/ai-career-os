package com.careeros.gateway;

import java.time.Duration;
import java.util.List;
import org.springframework.data.redis.core.ReactiveStringRedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.data.redis.core.script.RedisScript;
import reactor.core.publisher.Mono;

/**
 * The edge's budget, held where every replica can see it (Epic 120).
 *
 * <p>The problem this solves is arithmetic: {@link InProcessBudget} keeps one bucket per
 * process, and the production overlay runs three gateway replicas, so a caller's real
 * allowance is three times what the operator configured. Three edges each politely
 * enforcing a third of nothing is still nothing.
 *
 * <p>The whole decision is <b>one Lua script</b>, and that is the design rather than an
 * optimisation. A read-refill-write sequence issued as separate commands is a race: two
 * replicas read the same token count, both decide they may spend it, and the bucket
 * goes negative under exactly the concurrency it exists to bound. Redis evaluates a
 * script atomically, so the refill and the take happen with no other command in
 * between.
 *
 * <p>Refill is continuous rather than bursty: {@code elapsed * capacity / period}
 * tokens accrue, whole tokens are added, and the stamp advances only by the time those
 * whole tokens represent -- the sub-token remainder is kept, so a caller asking once a
 * second for an hour is not silently rounded to zero.
 *
 * <p>Errors are signals, not exceptions: the filter composes
 * {@code onErrorResume(...)} with the in-process budget, so a Redis outage becomes a
 * logged fallback instead of an open door or a closed one.
 */
public final class RedisBudget implements EdgeBudget {

    /** One key per identity; the hash holds the token count and the last refill stamp. */
    static final String KEY_PREFIX = "careeros:edge:rl:";

    /**
     * KEYS[1] bucket, ARGV[1] capacity, ARGV[2] period ms, ARGV[3] now ms.
     * Returns 1 when a token was spent, 0 when the bucket was empty.
     */
    static final String SCRIPT = """
            local capacity = tonumber(ARGV[1])
            local period = tonumber(ARGV[2])
            local now = tonumber(ARGV[3])
            local tokens = tonumber(redis.call('HGET', KEYS[1], 't'))
            local stamp = tonumber(redis.call('HGET', KEYS[1], 's'))
            if tokens == nil or stamp == nil then
              tokens = capacity
              stamp = now
            end
            local elapsed = now - stamp
            if elapsed > 0 then
              local gained = elapsed * capacity / period
              local whole = math.floor(gained)
              if whole > 0 then
                tokens = math.min(capacity, tokens + whole)
                stamp = stamp + math.floor(whole * period / capacity)
              end
            end
            local allowed = 0
            if tokens >= 1 then
              tokens = tokens - 1
              allowed = 1
            end
            redis.call('HSET', KEYS[1], 't', tokens, 's', stamp)
            redis.call('PEXPIRE', KEYS[1], period * 3)
            return allowed
            """;

    private final ReactiveStringRedisTemplate redis;
    private final int capacity;
    private final Duration period;
    private final RedisScript<Long> script;

    public RedisBudget(ReactiveStringRedisTemplate redis, int capacity, Duration period) {
        this.redis = redis;
        this.capacity = Math.max(1, capacity);
        this.period = period;
        this.script = new DefaultRedisScript<>(SCRIPT, Long.class);
    }

    @Override
    public Mono<Boolean> take(String identity) {
        return redis.execute(script, List.of(KEY_PREFIX + identity),
                        String.valueOf(capacity),
                        String.valueOf(period.toMillis()),
                        String.valueOf(System.currentTimeMillis()))
                .next()
                .map(value -> value != null && value == 1L)
                // An empty answer is not an admission: a script that returned nothing is
                // a script this edge does not understand, and guessing "yes" there would
                // be the one guess that removes the limit entirely.
                .defaultIfEmpty(false);
    }

    @Override
    public String name() {
        return "redis";
    }

    String keyFor(String identity) {
        return KEY_PREFIX + identity;
    }
}
