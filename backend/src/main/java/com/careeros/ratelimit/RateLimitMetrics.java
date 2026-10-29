package com.careeros.ratelimit;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.stereotype.Component;

/**
 * The limiter's decisions, as a scrape sees them (roadmap 27.2).
 *
 * <p>One counter, tagged with the bucket that decided and the outcome it chose. Before this,
 * a refusal left no trace the server owned: the 429 was written to the client and nothing
 * else, so an operator could see a ceiling refusing traffic only by watching responses. The
 * tag values are the bucket names {@link RateLimitFilter#ruleFor} answers with, which are
 * also the Redis key prefixes, so the counter and the limiter agree on what a bucket is.
 *
 * <p>A request admitted by the fail-open branch counts as {@code allowed}: that is the
 * decision the server made, and the alternative -- dropping it because Redis was down --
 * would make an outage read as a quiet period on the one dashboard that should show it.
 *
 * <p>Meters are created on the bucket's first decision rather than at boot: a deployment that
 * never sees a mail call exports no mail series at all, and a query keyed on the bucket shows
 * nothing rather than a flat zero.
 */
@Component
public class RateLimitMetrics {

    /** Micrometer name; the Prometheus exporter renders dots as underscores and counters as `_total`. */
    static final String DECISIONS = "careeros.ratelimit.decisions";

    static final String ALLOWED = "allowed";
    static final String DENIED = "denied";

    private static final String DESCRIPTION = "Requests the rate limiter admitted or refused, by bucket";

    private final MeterRegistry registry;
    private final Map<String, Counter> counters = new ConcurrentHashMap<>();

    public RateLimitMetrics(MeterRegistry registry) {
        this.registry = registry;
    }

    /** One decision: which bucket answered, and whether the request was let through. */
    void record(String bucket, boolean admitted) {
        String outcome = admitted ? ALLOWED : DENIED;
        counters.computeIfAbsent(bucket + "/" + outcome, unused -> Counter.builder(DECISIONS)
                        .tag("bucket", bucket)
                        .tag("outcome", outcome)
                        .description(DESCRIPTION)
                        .register(registry))
                .increment();
    }
}
