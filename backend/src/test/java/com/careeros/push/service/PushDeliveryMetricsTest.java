package com.careeros.push.service;

import static org.assertj.core.api.Assertions.assertThat;

import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/**
 * The morning ring as Prometheus reads it (roadmap 33.3).
 *
 * <p>Each outcome is counted under its own tag, and only that tag: an acceptance and a refusal
 * are different readings of the same morning, and a deployment without keys is neither -- it is
 * the feature being off, which is why it gets its own tag rather than inflating the refusals an
 * operator would be paged for.
 *
 * <p>The minute clock's heartbeat (roadmap 35.1) is pinned as a gauge rather than a counter: a
 * counter that stops moving reads the same as a board with nothing due, while the gauge's value
 * is the last completed tick's epoch second and a stale one is what an alarm watches.
 */
class PushDeliveryMetricsTest {

    private SimpleMeterRegistry registry;
    private PushDeliveryMetrics metrics;

    @BeforeEach
    void setUp() {
        registry = new SimpleMeterRegistry();
        metrics = new PushDeliveryMetrics(registry);
    }

    private double count(String outcome) {
        return registry.get(PushDeliveryMetrics.DELIVERY).tag("outcome", outcome).counter().count();
    }

    private double lastTick() {
        return registry.get(PushDeliveryMetrics.LAST_DUE_TICK).gauge().value();
    }

    @Test
    void a_new_process_reads_no_wakes_at_all() {
        assertThat(count(PushDeliveryMetrics.SENT)).isZero();
        assertThat(count(PushDeliveryMetrics.GONE)).isZero();
        assertThat(count(PushDeliveryMetrics.REFUSED)).isZero();
        assertThat(count(PushDeliveryMetrics.NOT_CONFIGURED)).isZero();
    }

    @Test
    void theMinuteClockStartsAtBootAndMovesOnlyWhenATickFinishes() {
        long boot = (long) lastTick();
        assertThat(boot).isPositive();

        // The tick is anchored to the boot reading, not to a wall-clock date: the gauge's
        // claim is that it holds the epoch second of the tick that finished, and a fixed
        // date in the past turns "the tick moved it forward" red on the calendar, not on
        // the code. Sixty seconds after boot is the smallest step the minute clock takes.
        long firstTick = boot + 60;
        metrics.recordDueTick(OffsetDateTime.ofInstant(Instant.ofEpochSecond(firstTick), ZoneOffset.UTC));

        assertThat(lastTick()).isEqualTo(firstTick).isGreaterThan(boot);
    }

    @Test
    void each_outcome_is_counted_under_its_own_tag() {
        metrics.record(PushSender.Outcome.SENT);
        metrics.record(PushSender.Outcome.SENT);
        metrics.record(PushSender.Outcome.GONE);
        metrics.record(PushSender.Outcome.REFUSED);
        metrics.record(PushSender.Outcome.NOT_CONFIGURED);

        assertThat(count(PushDeliveryMetrics.SENT)).isEqualTo(2.0);
        assertThat(count(PushDeliveryMetrics.GONE)).isEqualTo(1.0);
        assertThat(count(PushDeliveryMetrics.REFUSED)).isEqualTo(1.0);
        assertThat(count(PushDeliveryMetrics.NOT_CONFIGURED))
                .as("a deployment with push turned off is not a refusing transport")
                .isEqualTo(1.0);
    }
}
