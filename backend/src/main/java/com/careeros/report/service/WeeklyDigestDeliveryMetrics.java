package com.careeros.report.service;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.util.concurrent.atomic.AtomicLong;
import org.springframework.stereotype.Component;

/**
 * The letter's mail, as a scrape sees it (roadmap 21.3, heartbeat 22.4).
 *
 * <p>Three readings travel to Prometheus from here. The counter answers what the transport did
 * with a letter, with the outcome as a tag, so the refusal rate is one division and the alarm
 * is one expression. The delivered gauge is the epoch second of the last letter the transport
 * accepted: a refusal moves the counter and leaves the gauge where it was. The sweep gauge is
 * the Monday clock's heartbeat -- moved by the scheduler after a completed compose, with or
 * without letters -- so a week that was never even composed is visible; no letter count can
 * show that, because a quiet week writes no letter either.
 *
 * <p>Both gauges start at the process's own boot time, not at zero, for the reason the
 * ingestion and nightly markers do: zero reads as an event in 1970 and would page a fresh
 * deploy before it has had a night to report. The delivered gauge is not alarmed on -- an
 * install with no accounts never writes a letter, and that is not a fault -- so it is for the
 * fleet's dashboards rather than a pager. The sweep gauge is alarmed on, at a window wider
 * than its weekly cadence: a Monday that never ran is a promise broken.
 *
 * <p>Every send is counted, the Monday sweep's and the retry clock's: the count is of letters
 * that reached a transport, not of nights that ran, and a retried letter that finally leaves
 * is one delivery. The retry is not the compose heartbeat: only the scheduler's completed
 * Monday pass moves it, not a letter that left on a Tuesday.
 */
@Component
public class WeeklyDigestDeliveryMetrics {

    /** Micrometer names; the Prometheus exporter renders dots as underscores. */
    static final String DELIVERY = "careeros.digest.delivery";
    static final String LAST_DELIVERED = "careeros.digest.last.delivered.timestamp";
    static final String LAST_SWEEP = "careeros.digest.last.sweep.timestamp";

    /** The tag values; the outcome is a tag, not half a metric name. */
    static final String SENT = "sent";
    static final String REFUSED = "refused";

    private static final String DELIVERY_DESCRIPTION = "Weekly letters, tagged with what the mail transport did";

    private final Counter sent;
    private final Counter refused;
    private final AtomicLong lastDelivered;
    private final AtomicLong lastSweep;

    public WeeklyDigestDeliveryMetrics(MeterRegistry registry) {
        this.sent = Counter.builder(DELIVERY).tag("outcome", SENT)
                .description(DELIVERY_DESCRIPTION)
                .register(registry);
        this.refused = Counter.builder(DELIVERY).tag("outcome", REFUSED)
                .description(DELIVERY_DESCRIPTION)
                .register(registry);
        long boot = Instant.now().getEpochSecond();
        this.lastDelivered = new AtomicLong(boot);
        Gauge.builder(LAST_DELIVERED, lastDelivered, AtomicLong::doubleValue)
                .description("Epoch seconds of the last weekly letter the transport accepted")
                .register(registry);
        this.lastSweep = new AtomicLong(boot);
        Gauge.builder(LAST_SWEEP, lastSweep, AtomicLong::doubleValue)
                .description("Epoch seconds of the last Monday compose that finished")
                .register(registry);
    }

    /** The transport took one letter; the marker moves to the letter's own receipt. */
    void recordSent(OffsetDateTime deliveredAt) {
        sent.increment();
        lastDelivered.set(deliveredAt.toEpochSecond());
    }

    /** The transport refused one letter; the marker stays where the last success left it. */
    void recordRefused() {
        refused.increment();
    }

    /** The Monday compose finished; the heartbeat moves even when the week had no accounts. */
    void recordSweep(OffsetDateTime finishedAt) {
        lastSweep.set(finishedAt.toEpochSecond());
    }
}
