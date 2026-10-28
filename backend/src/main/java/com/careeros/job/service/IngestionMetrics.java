package com.careeros.job.service;

import com.careeros.job.entity.IngestionRun;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.util.concurrent.atomic.AtomicLong;
import org.springframework.stereotype.Component;

/**
 * The night, as a scrape sees it (roadmap 19.9).
 *
 * <p>Two readings travel to Prometheus from here. The counter answers how the runs ended,
 * with the outcome as a tag rather than in the name, so a failure rate is one division and
 * a new outcome would be a tag value instead of a new metric. The gauge is the epoch second
 * of the last run that <em>completed</em>: a night of failures moves the counter and leaves
 * the gauge where it was, which is what lets a rule ask "no successful sweep for 26 hours"
 * as {@code time() - careers_ingestion_last_success_timestamp}.
 *
 * <p>The gauge starts at the process's own boot time, not at zero. Zero would read as a
 * success in 1970 and page on every fresh deploy, before the first night has had a chance
 * to run; boot time gives a new process the same 26 hours a healthy one gets between nights.
 *
 * <p>Every run is recorded, the night's and the one a reader asks for by hand: the counter
 * counts pulls, and a manual pull that failed is exactly as much a failed pull.
 */
@Component
public class IngestionMetrics {

    /** Micrometer names; the Prometheus exporter renders dots as underscores. */
    static final String RUNS = "careeros.ingestion.runs";
    static final String LAST_SUCCESS = "careeros.ingestion.last.success.timestamp";

    private static final String RUNS_DESCRIPTION = "Ingestion runs, tagged with how the run ended";

    private final Counter completed;
    private final Counter failed;
    private final AtomicLong lastSuccess;

    public IngestionMetrics(MeterRegistry registry) {
        this.completed = Counter.builder(RUNS).tag("status", IngestionRun.STATUS_COMPLETED)
                .description(RUNS_DESCRIPTION)
                .register(registry);
        this.failed = Counter.builder(RUNS).tag("status", IngestionRun.STATUS_FAILED)
                .description(RUNS_DESCRIPTION)
                .register(registry);
        this.lastSuccess = new AtomicLong(Instant.now().getEpochSecond());
        Gauge.builder(LAST_SUCCESS, lastSuccess, AtomicLong::doubleValue)
                .description("Epoch seconds of the last ingestion run that completed")
                .register(registry);
    }

    /**
     * One finished run. A completed run also moves the success marker; a failed one must
     * not, or the alert above it would report the thing it exists to catch as a success.
     */
    void record(String status, OffsetDateTime finishedAt) {
        if (IngestionRun.STATUS_COMPLETED.equals(status)) {
            completed.increment();
            lastSuccess.set(finishedAt.toEpochSecond());
        } else {
            failed.increment();
        }
    }
}
