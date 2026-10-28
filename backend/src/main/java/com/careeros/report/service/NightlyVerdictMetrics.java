package com.careeros.report.service;

import com.careeros.report.dto.NightlyReportDtos.NightlyVerdict;
import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import java.time.Instant;
import java.util.concurrent.atomic.AtomicLong;
import org.springframework.stereotype.Component;

/**
 * The install's verdict, as a scrape sees it (roadmap 20.3).
 *
 * <p>Two readings travel to Prometheus from here. The marker is the epoch second the newest
 * nightly record <em>finished</em>, passed or failed: the cadence alarm asks whether records
 * are still arriving at all, so a failed night is still an arrival and moves it -- the failures
 * have their own gauge. The streak is the count of newest nights in a row that ended failed,
 * the same number the monitoring page's warning strip reads.
 *
 * <p>The marker starts at the process's own boot time, not at zero: zero would read as a
 * finish in 1970 and page on every fresh deploy before the first night has had a chance to
 * report, while boot time gives a new process the same 36 hours a healthy install gets. A
 * verdict with no finish -- an install that has never recorded -- leaves the marker where it
 * was for the same reason: "missing" is a fact for the page, and for the pager it is silence,
 * not a fresh timestamp.
 */
@Component
public class NightlyVerdictMetrics {

    /** Micrometer names; the Prometheus exporter renders dots as underscores. */
    static final String LAST_FINISHED = "careeros.nightly.last.finished.timestamp";
    static final String CONSECUTIVE_FAILURES = "careeros.nightly.consecutive.failures";

    private final AtomicLong lastFinished;
    private final AtomicLong consecutiveFailures;

    public NightlyVerdictMetrics(MeterRegistry registry) {
        this.lastFinished = new AtomicLong(Instant.now().getEpochSecond());
        this.consecutiveFailures = new AtomicLong(0);
        Gauge.builder(LAST_FINISHED, lastFinished, AtomicLong::doubleValue)
                .description("Epoch seconds of the newest nightly record's finish, passed or failed")
                .register(registry);
        Gauge.builder(CONSECUTIVE_FAILURES, consecutiveFailures, AtomicLong::doubleValue)
                .description("Newest nightly records in a row that ended failed")
                .register(registry);
    }

    /**
     * One verdict read. The streak is always published -- zero is the truth after a pass -- but
     * a missing verdict must not fabricate a finish.
     */
    void publish(NightlyVerdict verdict) {
        if (verdict.finishedAt() != null) {
            lastFinished.set(verdict.finishedAt().toEpochSecond());
        }
        consecutiveFailures.set(verdict.consecutiveFailures());
    }
}
