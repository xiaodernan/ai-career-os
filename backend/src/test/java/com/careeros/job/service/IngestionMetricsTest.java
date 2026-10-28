package com.careeros.job.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

import com.careeros.job.entity.IngestionRun;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/**
 * The night as Prometheus reads it (roadmap 19.9).
 *
 * <p>Three claims. Both counters start at zero and the success marker starts at boot,
 * not at the epoch, so a fresh process is not paged before its first night. A completed
 * run moves the marker to the run's own end time, not to "now" -- the gauge is a fact
 * about the run, and tests pin it to a fixed instant. A failed run is counted as failed
 * and moves nothing else; that asymmetry is the entire alert.
 */
class IngestionMetricsTest {

    private SimpleMeterRegistry registry;
    private IngestionMetrics metrics;

    @BeforeEach
    void setUp() {
        registry = new SimpleMeterRegistry();
        metrics = new IngestionMetrics(registry);
    }

    private double counter(String status) {
        return registry.get(IngestionMetrics.RUNS).tag("status", status).counter().count();
    }

    private double lastSuccess() {
        return registry.get(IngestionMetrics.LAST_SUCCESS).gauge().value();
    }

    private static OffsetDateTime at(int hour, int minute) {
        return OffsetDateTime.of(2026, 10, 28, hour, minute, 0, 0, ZoneOffset.UTC);
    }

    @Test
    void a_new_process_has_both_counters_at_zero_and_a_success_marker_at_its_own_boot() {
        assertThat(counter(IngestionRun.STATUS_COMPLETED)).isZero();
        assertThat(counter(IngestionRun.STATUS_FAILED)).isZero();
        assertThat(lastSuccess())
                .as("boot time, so a deploy gets the same 26 hours a healthy night gets")
                .isCloseTo(Instant.now().getEpochSecond(), within(10.0));
    }

    @Test
    void a_completed_run_moves_the_success_marker_to_the_runs_own_end() {
        OffsetDateTime finishedAt = at(3, 24);

        metrics.record(IngestionRun.STATUS_COMPLETED, finishedAt);

        assertThat(counter(IngestionRun.STATUS_COMPLETED)).isEqualTo(1.0);
        assertThat(counter(IngestionRun.STATUS_FAILED)).isZero();
        assertThat(lastSuccess()).isEqualTo((double) finishedAt.toEpochSecond());
    }

    @Test
    void a_failed_run_is_counted_and_leaves_the_success_marker_where_it_was() {
        OffsetDateTime completedAt = at(3, 20);

        metrics.record(IngestionRun.STATUS_COMPLETED, completedAt);
        metrics.record(IngestionRun.STATUS_FAILED, completedAt.plusMinutes(2));

        assertThat(counter(IngestionRun.STATUS_FAILED)).isEqualTo(1.0);
        assertThat(counter(IngestionRun.STATUS_COMPLETED)).isEqualTo(1.0);
        assertThat(lastSuccess())
                .as("a night of failures must not read as a success")
                .isEqualTo((double) completedAt.toEpochSecond());
    }
}
