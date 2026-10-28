package com.careeros.report.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

import com.careeros.report.dto.NightlyReportDtos.NightlyVerdict;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/**
 * The install's verdict as Prometheus reads it (roadmap 20.3).
 *
 * <p>Three claims. A new process reads boot time and no streak, so a deploy is not paged
 * before its first night has had a chance to report. A published verdict moves the finish
 * marker to the night's own finish -- not to "now" -- and carries the streak verbatim,
 * because the alarm and the page warn at the same count. A missing verdict moves the streak
 * to zero but never fabricates a finish: an install that has never recorded is silence on
 * the wire, and silence is what the stale rule exists to catch.
 */
class NightlyVerdictMetricsTest {

    private SimpleMeterRegistry registry;
    private NightlyVerdictMetrics metrics;

    @BeforeEach
    void setUp() {
        registry = new SimpleMeterRegistry();
        metrics = new NightlyVerdictMetrics(registry);
    }

    private double lastFinished() {
        return registry.get(NightlyVerdictMetrics.LAST_FINISHED).gauge().value();
    }

    private double streak() {
        return registry.get(NightlyVerdictMetrics.CONSECUTIVE_FAILURES).gauge().value();
    }

    private static OffsetDateTime at(int hour, int minute) {
        return OffsetDateTime.of(2026, 10, 27, hour, minute, 0, 0, ZoneOffset.UTC);
    }

    private static NightlyVerdict verdict(String status, OffsetDateTime finishedAt, int streak) {
        return new NightlyVerdict(status, finishedAt, "d8199f8",
                "https://github.example/actions/runs/1", streak, false, 36);
    }

    @Test
    void a_new_process_reads_boot_time_and_no_streak() {
        assertThat(lastFinished())
                .as("boot time, so a deploy gets the same 36 hours a healthy install gets")
                .isCloseTo(Instant.now().getEpochSecond(), within(10.0));
        assertThat(streak()).isZero();
    }

    @Test
    void a_published_verdict_moves_the_marker_to_the_nights_own_finish_and_carries_the_streak() {
        metrics.publish(verdict("failed", at(3, 41), 3));

        assertThat(lastFinished()).isEqualTo((double) at(3, 41).toEpochSecond());
        assertThat(streak()).isEqualTo(3.0);
    }

    @Test
    void a_passed_verdict_ends_the_streak_and_still_moves_the_marker() {
        metrics.publish(verdict("failed", at(3, 41), 2));
        metrics.publish(verdict("passed", at(3, 44).plusDays(1), 0));

        assertThat(lastFinished()).isEqualTo((double) at(3, 44).plusDays(1).toEpochSecond());
        assertThat(streak()).isZero();
    }

    @Test
    void a_missing_verdict_publishes_no_finish_and_no_streak() {
        metrics.publish(new NightlyVerdict(NightlyVerdict.MISSING, null, null, null, 0, true, 36));

        assertThat(lastFinished())
                .as("silence stays silence; a fabricated 'now' would mute the stale alarm for 36 hours")
                .isCloseTo(Instant.now().getEpochSecond(), within(10.0));
        assertThat(streak()).isZero();
    }
}
