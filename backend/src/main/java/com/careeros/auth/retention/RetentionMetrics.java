package com.careeros.auth.retention;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.stereotype.Component;

/**
 * The retention sweep's one reading (roadmap 28.1): how many expired rows each table gave up,
 * tagged by table.
 *
 * <p>A sweep that removes nothing and a sweep that never ran look the same in a log file that
 * scrolled away; the counter separates them, because a nightly sweep is visible as a flat line
 * at zero and a stopped one is no line at all. The tag is registered on the first sweep over
 * that table rather than at boot, so an install that has never accumulated a reset token does
 * not export a series pretending it has been pruning one.
 */
@Component
public class RetentionMetrics {

    static final String DELETED = "careeros.retention.deleted_rows";
    private static final String DESCRIPTION =
            "Expired credential rows removed by the retention sweep, by table";

    private final MeterRegistry registry;
    private final Map<String, Counter> counters = new ConcurrentHashMap<>();

    public RetentionMetrics(MeterRegistry registry) {
        this.registry = registry;
    }

    void record(String table, int rows) {
        counters.computeIfAbsent(table, name -> Counter.builder(DELETED)
                        .tag("table", name)
                        .description(DESCRIPTION)
                        .register(registry))
                .increment(rows);
    }
}
