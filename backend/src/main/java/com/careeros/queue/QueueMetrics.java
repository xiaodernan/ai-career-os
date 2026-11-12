package com.careeros.queue;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.stereotype.Component;

/**
 * The queue's one meter: {@code careeros.queue.jobs}, tagged by kind and outcome.
 *
 * <p>Outcomes are the two producers' ({@code enqueued}, {@code dropped}) and the four a tick
 * can reach ({@code done}, {@code failed}, {@code dead}, {@code reclaimed}). {@code failed}
 * counts an attempt that left the job in the PEL for a sibling to retry; {@code dead} counts
 * a job that stopped being retried. The pair is what separates a busy queue from a stuck one.
 *
 * <p>The kind tag is taken from the registered handler's own name, never from the wire field,
 * so a malformed entry cannot mint a new time series per bad payload.
 */
@Component
public class QueueMetrics {

    /** The meter's name, public so the integration suite can read it off the registry -- a tagged counter cannot be asserted by name otherwise. */
    public static final String JOBS = "careeros.queue.jobs";
    private static final String DESCRIPTION = "Backend queue jobs, by kind and outcome";

    private final MeterRegistry registry;
    private final Map<String, Counter> counters = new ConcurrentHashMap<>();

    public QueueMetrics(MeterRegistry registry) {
        this.registry = registry;
    }

    public void count(String kind, String outcome) {
        counters.computeIfAbsent(kind + "/" + outcome, unused -> Counter.builder(JOBS)
                        .tag("kind", kind)
                        .tag("outcome", outcome)
                        .description(DESCRIPTION)
                        .register(registry))
                .increment();
    }
}