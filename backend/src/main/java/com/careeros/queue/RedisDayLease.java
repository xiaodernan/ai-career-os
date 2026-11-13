package com.careeros.queue;

import java.time.Duration;
import java.time.LocalDate;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

/**
 * One fleet-wide lease per UTC calendar day, Redis-backed (Epic 169).
 *
 * <p>Every {@code @Scheduled} job in this fleet used to fire on every replica at the
 * same instant; only a process-local fact could have made them disagree — there was
 * none. The day-keyed lease gives each node the same answer within the day: one
 * replica acquires the lease and does the work; everyone else sees the same verdict
 * and stands down. A replica that dies mid-day simply never runs today's pass again;
 * the heartbeat the job moves is the operator's instrument for noticing that.
 *
 * <p>The lease is timeboxed to the UTC day it names, and the key records the name of
 * the business concern it guards (e.g. {@code retention}, {@code digest.compose}) so a
 * stuck lease from a previous day can never bleed into today's answer: the key is
 * derived from today, never written by yesterday's winner.
 */
@Component
public final class RedisDayLease {

    /** Shared prefix; the suffix is {@code <concern>:<yyyy-MM-dd>}. */
    public static final String KEY_PREFIX = "careeros:v1:lease:";

    private final StringRedisTemplate redis;

    public RedisDayLease(StringRedisTemplate redis) {
        this.redis = redis;
    }

    /** The key this day's lease lives under — exposed for the tests and the operator. */
    public static String keyOf(String concern, LocalDate day) {
        return KEY_PREFIX + concern + ":" + day;
    }

    /**
     * True when this replica acquired today's lease for {@code concern} right now.
     * A Redis failure <em>throws</em>: callers decide what failing closed toward the work
     * means for their own concern — for a sweep, one duplicated pass beats a skipped one.
     */
    public boolean tryAcquire(String concern, LocalDate day) {
        Boolean held = redis.opsForValue()
                .setIfAbsent(keyOf(concern, day), "1", Duration.ofDays(1));
        return Boolean.TRUE.equals(held);
    }
}
