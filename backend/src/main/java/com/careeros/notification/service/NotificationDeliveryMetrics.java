package com.careeros.notification.service;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.util.concurrent.atomic.AtomicLong;
import org.springframework.stereotype.Component;

/**
 * The signal mail, as a scrape sees it (roadmap 22.2, heartbeat 22.3).
 *
 * <p>Three readings travel to Prometheus from here. The counter answers what the transport did
 * with one account's morning letter, with the outcome as a tag, so the refusal rate is one
 * division and the alarm is one expression. The delivered gauge is the epoch second of the last
 * letter the transport accepted: a refusal moves the counter and leaves the gauge where it was.
 * The sweep gauge is the heartbeat -- it moves at the end of every completed pass, with or
 * without letters -- so a clock that stopped can be told apart from an inbox that is quiet.
 *
 * <p>Both gauges start at the process's own boot time, for the reason the digest's marker does:
 * zero reads as an event in 1970 and would page a fresh deploy before it has had a morning to
 * report. The delivered gauge is not alarmed on -- an install whose accounts have nothing
 * waiting writes no letter, and a quiet inbox is not a fault -- so it is for dashboards rather
 * than a pager. The sweep gauge is alarmed on: a pass that never ran is a promise broken, and
 * no other reading would show it.
 *
 * <p>Every accepted letter is counted, whether it carried one signal or forty: the count is of
 * accounts reached, not of items mailed. A letter that was never attempted -- an account with
 * no row or no address -- is not a refusal and is not counted here; it is a warn line, because
 * the transport was never asked. A pass that could not even read its audience never reaches
 * the heartbeat: there was no sweep.
 */
@Component
public class NotificationDeliveryMetrics {

    /** Micrometer names; the Prometheus exporter renders dots as underscores. */
    static final String DELIVERY = "careeros.signals.delivery";
    static final String LAST_DELIVERED = "careeros.signals.last.delivered.timestamp";
    static final String LAST_SWEEP = "careeros.signals.last.sweep.timestamp";

    /** The tag values; the outcome is a tag, not half a metric name. */
    static final String SENT = "sent";
    static final String REFUSED = "refused";

    private static final String DELIVERY_DESCRIPTION = "Signal mails, tagged with what the mail transport did";

    private final Counter sent;
    private final Counter refused;
    private final AtomicLong lastDelivered;
    private final AtomicLong lastSweep;

    public NotificationDeliveryMetrics(MeterRegistry registry) {
        this.sent = Counter.builder(DELIVERY).tag("outcome", SENT)
                .description(DELIVERY_DESCRIPTION)
                .register(registry);
        this.refused = Counter.builder(DELIVERY).tag("outcome", REFUSED)
                .description(DELIVERY_DESCRIPTION)
                .register(registry);
        long boot = Instant.now().getEpochSecond();
        this.lastDelivered = new AtomicLong(boot);
        Gauge.builder(LAST_DELIVERED, lastDelivered, AtomicLong::doubleValue)
                .description("Epoch seconds of the last signal mail the transport accepted")
                .register(registry);
        this.lastSweep = new AtomicLong(boot);
        Gauge.builder(LAST_SWEEP, lastSweep, AtomicLong::doubleValue)
                .description("Epoch seconds of the last signal-mail sweep that finished")
                .register(registry);
    }

    /** The transport took one account's letter; the marker moves to the acceptance itself. */
    void recordSent(OffsetDateTime acceptedAt) {
        sent.increment();
        lastDelivered.set(acceptedAt.toEpochSecond());
    }

    /** The transport refused one account's letter; the marker stays where the last success left it. */
    void recordRefused() {
        refused.increment();
    }

    /** One pass finished; the heartbeat moves whether or not it had letters to send. */
    void recordSweep(OffsetDateTime finishedAt) {
        lastSweep.set(finishedAt.toEpochSecond());
    }
}
