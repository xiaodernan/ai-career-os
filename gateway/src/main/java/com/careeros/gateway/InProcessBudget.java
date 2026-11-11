package com.careeros.gateway;

import io.github.resilience4j.ratelimiter.RateLimiter;
import io.github.resilience4j.ratelimiter.RateLimiterConfig;
import java.time.Duration;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import reactor.core.publisher.Mono;

/**
 * The budget this process keeps for itself (Epic 89.2, unchanged in behaviour).
 *
 * <p>One token bucket per identity, in a map that is bounded: the identity of an
 * anonymous caller is its address, so an edge exposed to the internet sees a new key
 * per scanner. An unbounded map is a slow leak in the one process that must not have
 * one, so the map flushes when it passes {@code maxIdentities}. A flush is safe in the
 * direction that matters -- every bucket starts full again, which is lenient for one
 * period, never stricter than the operator configured.
 */
public final class InProcessBudget implements EdgeBudget {

    /** Enough identities for a busy single edge, small enough to stay a rounding error. */
    static final int DEFAULT_MAX_IDENTITIES = 50_000;

    private final int tokensPerPeriod;
    private final Duration period;
    private final int maxIdentities;
    private final Map<String, RateLimiter> limiters = new ConcurrentHashMap<>();
    private long flushes;

    public InProcessBudget(int tokensPerPeriod, Duration period) {
        this(tokensPerPeriod, period, DEFAULT_MAX_IDENTITIES);
    }

    InProcessBudget(int tokensPerPeriod, Duration period, int maxIdentities) {
        this.tokensPerPeriod = tokensPerPeriod;
        this.period = period;
        this.maxIdentities = Math.max(1, maxIdentities);
    }

    @Override
    public Mono<Boolean> take(String identity) {
        if (tokensPerPeriod <= 0) {
            return Mono.just(true);
        }
        if (limiters.size() > maxIdentities) {
            limiters.clear();
            flushes++;
        }
        RateLimiter limiter = limiters.computeIfAbsent(identity,
                key -> RateLimiter.of("edge", RateLimiterConfig.custom()
                        .limitForPeriod(tokensPerPeriod)
                        .limitRefreshPeriod(period)
                        .timeoutDuration(Duration.ZERO)
                        .build()));
        return Mono.just(limiter.acquirePermission());
    }

    @Override
    public String name() {
        return "in-process";
    }

    /** How many times the identity map was flushed; pinned by the test that bounds it. */
    public long flushes() {
        return flushes;
    }

    public int size() {
        return limiters.size();
    }
}
