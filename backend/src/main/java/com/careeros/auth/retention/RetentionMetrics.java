package com.careeros.auth.retention;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;
import org.springframework.stereotype.Component;

/**
 * The retention sweep's readings (roadmap 28.1, heartbeat 28.2): how many expired rows each
 * table gave up, tagged by table, and when the sweep last finished.
 *
 * <p>The counter answers how much a sweep removed; the gauge answers whether the clock still
 * runs. Neither answers the other's question: a stopped sweep leaves the counters at their last
 * value, which a scrape cannot tell from a quiet night, and a sweep that deletes nothing still
 * has to prove it happened. So the gauge moves at the end of every completed pass, with or
 * without rows, and an alarm reads its age. The tag is registered on the first sweep over that
 * table rather than at boot, so an install that has never accumulated a reset token does not
 * export a series pretending it has been pruning one.
 *
 * <p>The gauge starts at the process's own boot time, not at zero, for the reason the other
 * sweep markers do: zero reads as an event in 1970 and would page a fresh deploy before its
 * first 04:47. A pass whose every table failed still moves it, because the question is whether
 * the scheduler ran -- the failures are already a WARN line and a missing per-table reading,
 * and muting the heartbeat would turn a database outage into a silent install.
 */
@Component
public class RetentionMetrics {

    static final String DELETED = "careeros.retention.deleted_rows";
    static final String LAST_SWEEP = "careeros.retention.last.sweep.timestamp";
    private static final String DESCRIPTION =
            "Expired credential rows removed by the retention sweep, by table";

    private final MeterRegistry registry;
    private final Map<String, Counter> counters = new ConcurrentHashMap<>();
    private final AtomicLong lastSweep;

    public RetentionMetrics(MeterRegistry registry) {
        this.registry = registry;
        this.lastSweep = new AtomicLong(Instant.now().getEpochSecond());
        Gauge.builder(LAST_SWEEP, lastSweep, AtomicLong::doubleValue)
                .description("Epoch seconds of the last retention sweep that finished")
                .register(registry);
    }

    void record(String table, int rows) {
        counters.computeIfAbsent(table, name -> Counter.builder(DELETED)
                        .tag("table", name)
                        .description(DESCRIPTION)
                        .register(registry))
                .increment(rows);
    }

    /** One completed pass, with or without deletions and with or without a failed table. */
    void recordSweep(OffsetDateTime finishedAt) {
        lastSweep.set(finishedAt.toEpochSecond());
    }
}
