package com.careeros.push.service;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.util.EnumMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicLong;
import org.springframework.stereotype.Component;

/**
 * The morning ring, as a scrape sees it (roadmap 33.3).
 *
 * <p>One counter, tagged with what the push transport did with one registration: {@code sent},
 * {@code gone} (the push service retired the registration and the sweep deleted it), {@code
 * refused} (a service that answered with something other than an acceptance), and {@code
 * not_configured} (the deployment ships no VAPID keys, so no browser could have rung). The last
 * tag is deliberately not folded into {@code refused}: a quiet install with push turned off is
 * not a failing transport, and an operator who adds keys should see the tag that explains the
 * flat mornings before it does.
 *
 * <p>Two passes ring: the morning one that rides the signal mail, and the minute clock a due
 * reminder wakes on (roadmap 35.1). The morning pass has no heartbeat of its own -- it rides the
 * signal mail's sweep gauge, and a pass that died before reaching the ring still leaves that
 * gauge stale because the scheduler runs both halves and catches them separately. The minute
 * clock has no such neighbour, so it carries its own gauge: {@code
 * careeros.reminders.last.tick.timestamp} moves at the end of every completed tick, with or
 * without a reminder to ring, so a clock that stopped can be told from a board with nothing due.
 * Both start at the process's own boot time, for the reason the mail sweep's marker gives.
 */
@Component
public class PushDeliveryMetrics {

    /** Micrometer name; the Prometheus exporter renders dots as underscores. */
    static final String DELIVERY = "careeros.push.delivery";
    static final String LAST_DUE_TICK = "careeros.reminders.last.tick.timestamp";

    static final String SENT = "sent";
    static final String GONE = "gone";
    static final String REFUSED = "refused";
    static final String NOT_CONFIGURED = "not_configured";

    private static final String DESCRIPTION =
            "Web Push wakes, tagged with what the push transport did";

    private final Map<PushSender.Outcome, Counter> counters =
            new EnumMap<>(PushSender.Outcome.class);
    private final AtomicLong lastDueTick;

    public PushDeliveryMetrics(MeterRegistry registry) {
        counters.put(PushSender.Outcome.SENT, counter(registry, SENT));
        counters.put(PushSender.Outcome.GONE, counter(registry, GONE));
        counters.put(PushSender.Outcome.REFUSED, counter(registry, REFUSED));
        counters.put(PushSender.Outcome.NOT_CONFIGURED, counter(registry, NOT_CONFIGURED));
        long boot = Instant.now().getEpochSecond();
        this.lastDueTick = new AtomicLong(boot);
        Gauge.builder(LAST_DUE_TICK, lastDueTick, AtomicLong::doubleValue)
                .description("Epoch seconds of the last reminder-ring tick that finished")
                .register(registry);
    }

    private static Counter counter(MeterRegistry registry, String outcome) {
        return Counter.builder(DELIVERY).tag("outcome", outcome).description(DESCRIPTION)
                .register(registry);
    }

    /** One registration was asked to wake; its outcome is counted under its own tag. */
    public void record(PushSender.Outcome outcome) {
        counters.get(outcome).increment();
    }

    /** One minute tick finished; the heartbeat moves whether or not anything was due. */
    public void recordDueTick(OffsetDateTime finishedAt) {
        lastDueTick.set(finishedAt.toEpochSecond());
    }
}
