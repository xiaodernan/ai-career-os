package com.careeros.queue;

import java.time.Duration;
import java.time.LocalDate;
import org.springframework.data.redis.core.StringRedisTemplate;

/**
 * A standing fleet lease with a short TTL, Redis-backed (Epic 171).
 *
 * <p>Day-long leases protect a sweep; this one protects a clock that fires every minute,
 * and it exists because the day driver cannot say "one node for the life of the
 * process" — a node won by a lease that expires every minute would drop the clock's
 * rhythm every minute. The short lease (90s, longer than the interval between ticks)
 * gives one node continuous custody — the fleet's current answer to "whose clock
is this?" — with a takeover a minute after a crash, which is the smallest honest
 * inheritance a minute clock can have.
 *
 * <p>Exactly one node wins per window: Redis setIfAbsent is atomic. The loser returns
 * false without touching the transport; the winner works; a crashed holder's lease
 * lapses and its successor acquires on its next ping. Nobody holds two keys: the node
 * that ran the last minute re-acquires for the next one — refresh-by-default is the
 * right semantics for a standing lease, unlike a claim the holder must remember to
 * renew.
 */
public final class RedisShortLease {

    /** The shared prefix; nothing else is needed because the TTL carries the freshness. */
    public static final String KEY_PREFIX = "careeros:v1:lease:";

    private final String name;
    private final StringRedisTemplate redis;

    public RedisShortLease(String name, StringRedisTemplate redis) {
        this.name = name;
        this.redis = redis;
    }

    /** The key this lease lives under — exposed for the tests and the operator. */
    public String key() {
        return KEY_PREFIX + name;
    }

    /**
     * True when this node acquired the lease now; false when a sibling holds it, or while
     * the current holder's 90-second key is still fresh. Note: this node's own fresh key
     * blocks it too, so custody rotates through the fleet on each TTL — that is the
     * correct behaviour for a standing minute lease: at most one node rings any minute,
     * and every acquisition is a clean handover with the latches doing the de-dupe.
     *
     * A Redis failure <em>throws</em>; the minute clock closes rather than duplicates —
     * a risky chime twice can wake a phone, a silent minutes gap is what the heartbeat
     * alarm is for (5 missed ticks trips the rule). Caller handles it.
     */
    public boolean tryAcquire(Duration ttl) {
        Boolean held = redis.opsForValue().setIfAbsent(key(), "1", ttl);
        return Boolean.TRUE.equals(held);
    }
}
