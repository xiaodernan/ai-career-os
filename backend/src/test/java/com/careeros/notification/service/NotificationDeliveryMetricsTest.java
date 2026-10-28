package com.careeros.notification.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/**
 * The signal mail as Prometheus reads it (roadmap 22.2, heartbeat 22.3).
 *
 * <p>Five claims. A new process reads boot time on both markers and no deliveries, so a deploy
 * is not paged for mail it has not had a morning to send. An acceptance moves the delivered
 * marker to the moment the transport took the letter -- not to "now" and not to any item's own
 * time -- and increments only the sent counter. A refusal increments only the refused counter
 * and leaves the delivered marker where the last acceptance put it, because a refusal that
 * moved it would mute the one reading that says mail is leaving at all. A finished sweep moves
 * the heartbeat even with nothing to send, and a sweep is not a delivery: the two markers are
 * different promises. A refusal moves neither marker.
 */
class NotificationDeliveryMetricsTest {

    private SimpleMeterRegistry registry;
    private NotificationDeliveryMetrics metrics;

    @BeforeEach
    void setUp() {
        registry = new SimpleMeterRegistry();
        metrics = new NotificationDeliveryMetrics(registry);
    }

    private double sent() {
        return registry.get(NotificationDeliveryMetrics.DELIVERY)
                .tag("outcome", NotificationDeliveryMetrics.SENT).counter().count();
    }

    private double refused() {
        return registry.get(NotificationDeliveryMetrics.DELIVERY)
                .tag("outcome", NotificationDeliveryMetrics.REFUSED).counter().count();
    }

    private double lastDelivered() {
        return registry.get(NotificationDeliveryMetrics.LAST_DELIVERED).gauge().value();
    }

    private double lastSweep() {
        return registry.get(NotificationDeliveryMetrics.LAST_SWEEP).gauge().value();
    }

    private static OffsetDateTime at(int hour, int minute) {
        return OffsetDateTime.of(2026, 10, 27, hour, minute, 0, 0, ZoneOffset.UTC);
    }

    @Test
    void a_new_process_reads_boot_time_and_no_deliveries() {
        assertThat(sent()).isZero();
        assertThat(refused()).isZero();
        assertThat(lastDelivered())
                .as("boot time, so a fresh deploy is not read as mail that stopped in 1970")
                .isCloseTo(Instant.now().getEpochSecond(), within(10.0));
        assertThat(lastSweep())
                .as("the heartbeat also starts at boot, so a fresh deploy is not stale")
                .isCloseTo(Instant.now().getEpochSecond(), within(10.0));
    }

    @Test
    void an_accepted_letter_moves_the_marker_to_its_acceptance_and_counts_one_delivery() {
        metrics.recordSent(at(7, 30));

        assertThat(sent()).isEqualTo(1.0);
        assertThat(refused()).isZero();
        assertThat(lastDelivered()).isEqualTo((double) at(7, 30).toEpochSecond());
    }

    @Test
    void a_refused_letter_is_counted_and_leaves_the_marker_where_the_last_success_left_it() {
        metrics.recordSent(at(7, 30));
        metrics.recordRefused();

        assertThat(sent()).isEqualTo(1.0);
        assertThat(refused()).isEqualTo(1.0);
        assertThat(lastDelivered())
                .as("a refusal is not a delivery; the marker moves only when a letter leaves")
                .isEqualTo((double) at(7, 30).toEpochSecond());
        assertThat(lastSweep())
                .as("a refusal is not a finished sweep either; the clock reports for itself")
                .isCloseTo(Instant.now().getEpochSecond(), within(10.0));
    }

    @Test
    void a_sweep_with_nothing_to_send_still_heartbeats_and_is_not_a_delivery() {
        metrics.recordSweep(at(7, 31));

        assertThat(lastSweep()).isEqualTo((double) at(7, 31).toEpochSecond());
        assertThat(sent()).isZero();
        assertThat(refused()).isZero();
        assertThat(lastDelivered())
                .as("a quiet morning is a heartbeat, not a letter")
                .isCloseTo(Instant.now().getEpochSecond(), within(10.0));
    }
}
