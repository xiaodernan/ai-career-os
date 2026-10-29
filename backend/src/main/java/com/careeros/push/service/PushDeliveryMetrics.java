package com.careeros.push.service;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import java.util.EnumMap;
import java.util.Map;
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
 * <p>There is no second heartbeat here. The ring rides the same morning pass as the signal mail,
 * and that pass's own heartbeat ({@code careeros.signals.last.sweep}) already answers "did the
 * clock run"; a ring that never happened is read off the {@code sent} counter staying flat while
 * subscriptions exist, and a pass that died before reaching the ring still leaves the heartbeat
 * stale because the scheduler runs both halves and catches them separately.
 */
@Component
public class PushDeliveryMetrics {

    /** Micrometer name; the Prometheus exporter renders dots as underscores. */
    static final String DELIVERY = "careeros.push.delivery";

    static final String SENT = "sent";
    static final String GONE = "gone";
    static final String REFUSED = "refused";
    static final String NOT_CONFIGURED = "not_configured";

    private static final String DESCRIPTION =
            "Web Push wakes, tagged with what the push transport did";

    private final Map<PushSender.Outcome, Counter> counters =
            new EnumMap<>(PushSender.Outcome.class);

    public PushDeliveryMetrics(MeterRegistry registry) {
        counters.put(PushSender.Outcome.SENT, counter(registry, SENT));
        counters.put(PushSender.Outcome.GONE, counter(registry, GONE));
        counters.put(PushSender.Outcome.REFUSED, counter(registry, REFUSED));
        counters.put(PushSender.Outcome.NOT_CONFIGURED, counter(registry, NOT_CONFIGURED));
    }

    private static Counter counter(MeterRegistry registry, String outcome) {
        return Counter.builder(DELIVERY).tag("outcome", outcome).description(DESCRIPTION)
                .register(registry);
    }

    /** One registration was asked to wake; its outcome is counted under its own tag. */
    public void record(PushSender.Outcome outcome) {
        counters.get(outcome).increment();
    }
}
