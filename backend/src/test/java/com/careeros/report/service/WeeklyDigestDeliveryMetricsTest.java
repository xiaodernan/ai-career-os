package com.careeros.report.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/**
 * The letter's mail as Prometheus reads it (roadmap 21.3, heartbeat 22.4).
 *
 * <p>Five claims. A new process reads boot time on both markers and no deliveries, so a
 * deploy is not paged for mail it has not had a Monday to send. A delivery moves the delivered
 * marker to the letter's own receipt -- not to "now" -- and increments only the sent counter.
 * A refusal increments only the refused counter and leaves the delivered marker where the
 * last acceptance put it, because a refusal that moved it would mute the one reading that says
 * mail is leaving at all. A finished compose moves the heartbeat even when the week wrote no
 * letters, and a compose is not a delivery. A refusal moves neither marker.
 */
class WeeklyDigestDeliveryMetricsTest {

    private SimpleMeterRegistry registry;
    private WeeklyDigestDeliveryMetrics metrics;

    @BeforeEach
    void setUp() {
        registry = new SimpleMeterRegistry();
        metrics = new WeeklyDigestDeliveryMetrics(registry);
    }

    private double sent() {
        return registry.get(WeeklyDigestDeliveryMetrics.DELIVERY)
                .tag("outcome", WeeklyDigestDeliveryMetrics.SENT).counter().count();
    }

    private double refused() {
        return registry.get(WeeklyDigestDeliveryMetrics.DELIVERY)
                .tag("outcome", WeeklyDigestDeliveryMetrics.REFUSED).counter().count();
    }

    private double lastDelivered() {
        return registry.get(WeeklyDigestDeliveryMetrics.LAST_DELIVERED).gauge().value();
    }

    private double lastSweep() {
        return registry.get(WeeklyDigestDeliveryMetrics.LAST_SWEEP).gauge().value();
    }

    private static OffsetDateTime at(int hour, int minute) {
        return OffsetDateTime.of(2026, 10, 27, hour, minute, 0, 0, ZoneOffset.UTC);
    }

    @Test
    void aNewProcessReadsBootTimeAndNoDeliveries() {
        assertThat(sent()).isZero();
        assertThat(refused()).isZero();
        assertThat(lastDelivered())
                .as("boot time, so a fresh deploy is not read as mail that stopped in 1970")
                .isCloseTo(Instant.now().getEpochSecond(), within(10.0));
        assertThat(lastSweep())
                .as("the Monday heartbeat also starts at boot, so a fresh deploy is not stale")
                .isCloseTo(Instant.now().getEpochSecond(), within(10.0));
    }

    @Test
    void anAcceptedLetterMovesTheMarkerToItsOwnReceiptAndCountsOneDelivery() {
        metrics.recordSent(at(9, 5));

        assertThat(sent()).isEqualTo(1.0);
        assertThat(refused()).isZero();
        assertThat(lastDelivered()).isEqualTo((double) at(9, 5).toEpochSecond());
    }

    @Test
    void aRefusedLetterIsCountedAndLeavesTheMarkerWhereTheLastSuccessLeftIt() {
        metrics.recordSent(at(9, 5));
        metrics.recordRefused();

        assertThat(sent()).isEqualTo(1.0);
        assertThat(refused()).isEqualTo(1.0);
        assertThat(lastDelivered())
                .as("a refusal is not a delivery; the marker moves only when a letter leaves")
                .isEqualTo((double) at(9, 5).toEpochSecond());
        assertThat(lastSweep())
                .as("a refusal is not a finished compose; the clock reports for itself")
                .isCloseTo(Instant.now().getEpochSecond(), within(10.0));
    }

    @Test
    void aMondayWithNothingToWriteStillHeartbeatsAndIsNotADelivery() {
        metrics.recordSweep(at(8, 0));

        assertThat(lastSweep()).isEqualTo((double) at(8, 0).toEpochSecond());
        assertThat(sent()).isZero();
        assertThat(refused()).isZero();
        assertThat(lastDelivered())
                .as("a quiet Monday is a heartbeat, not a letter")
                .isCloseTo(Instant.now().getEpochSecond(), within(10.0));
    }
}
