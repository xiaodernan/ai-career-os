package com.careeros.ai.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.ai.AiServiceClient;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.util.Map;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/**
 * The ai-service's queue/cache readings as Prometheus reads them (Epic 150).
 *
 * <p>These are gauge-of-a-cached-reading tests, the same shape as {@link AiUsageMetricsTest}:
 * a refresh publishes the numbers from one answer; a failed refresh keeps the last good reading
 * instead of publishing a zero that would clear a dashboard; and the two engine endpoints fail
 * independently so one bad read cannot blank the other's numbers. One extra case pins the honest
 * boundary this collector exists for -- the system id is sent (the engine requires it) but the
 * verdict's own diagnostic keys never become series.
 */
class AiOpsMetricsTest {

    private static final Map<String, Object> QUEUE = Map.of(
            "verdict", "degraded",
            "alerts", java.util.List.of("internal-only sentence"),
            "queue", Map.of("dlq_len", 3, "delayed_len", 7, "pending", 2, "ok", true,
                    "stream_len", 11, "dlq_enabled", true, "delayed_enabled", true),
            "guard", Map.of("enabled", true, "cooldown_s", 900, "cooled_count", 1),
            "backend", "redis");

    private static final Map<String, Object> CACHE = Map.of(
            "verdict", "ineffective",
            "observation_error", "describe-failed:TypeError",
            "cache", Map.of("hit_rate", 0.25, "errors", 4, "lookups", 100, "hits", 25),
            "enabled", true, "backend", "memory");

    private AiServiceClient ai;
    private SimpleMeterRegistry registry;
    /** Micrometer holds the gauge's object weakly; a field keeps the collector alive across a read. */
    private AiOpsMetrics constructed;

    @BeforeEach
    void setUp() {
        ai = mock(AiServiceClient.class);
        registry = new SimpleMeterRegistry();
        when(ai.workqueueVerdict(AiOpsMetrics.SYSTEM_USER_ID)).thenReturn(QUEUE);
        when(ai.cacheVerdict(AiOpsMetrics.SYSTEM_USER_ID)).thenReturn(CACHE);
    }

    private double gauge(String name) {
        return registry.get(name).gauge().value();
    }

    @Test
    void the_first_refresh_publishes_only_the_measured_numbers() {
        constructed = new AiOpsMetrics(ai, registry);

        assertThat(gauge(AiOpsMetrics.WORKQUEUE_DLQ)).isEqualTo(3.0);
        assertThat(gauge(AiOpsMetrics.WORKQUEUE_DELAYED)).isEqualTo(7.0);
        assertThat(gauge(AiOpsMetrics.WORKQUEUE_PENDING)).isEqualTo(2.0);
        assertThat(gauge(AiOpsMetrics.WORKQUEUE_OK)).isEqualTo(1.0);
        assertThat(gauge(AiOpsMetrics.CACHE_HIT_RATE)).isEqualTo(0.25);
        assertThat(gauge(AiOpsMetrics.CACHE_ERRORS)).isEqualTo(4.0);
        assertThat(gauge(AiOpsMetrics.SCRAPE_OK)).isEqualTo(1.0);
    }

    @Test
    void only_the_nil_system_id_is_sent_and_no_diagnostic_field_becomes_a_series() {
        constructed = new AiOpsMetrics(ai, registry);

        verify(ai).workqueueVerdict(AiOpsMetrics.SYSTEM_USER_ID);
        verify(ai).cacheVerdict(AiOpsMetrics.SYSTEM_USER_ID);
        assertThat(AiOpsMetrics.SYSTEM_USER_ID.toString())
                .isEqualTo("00000000-0000-0000-0000-000000000000");
        // The answer carries a verdict word, alert prose and diagnostic keys (observation_error,
        // degraded_to, ...). None of them becomes a series: the collector publishes exactly these
        // seven numeric gauges and nothing else, so a future field cannot leak in silently.
        assertThat(registry.getMeters())
                .extracting(m -> m.getId().getName())
                .containsExactlyInAnyOrder(
                        AiOpsMetrics.WORKQUEUE_DLQ, AiOpsMetrics.WORKQUEUE_DELAYED,
                        AiOpsMetrics.WORKQUEUE_PENDING, AiOpsMetrics.WORKQUEUE_OK,
                        AiOpsMetrics.CACHE_HIT_RATE, AiOpsMetrics.CACHE_ERRORS,
                        AiOpsMetrics.SCRAPE_OK);
    }

    @Test
    void a_failed_refresh_keeps_the_last_good_numbers_and_marks_the_scrape_down() {
        when(ai.workqueueVerdict(AiOpsMetrics.SYSTEM_USER_ID))
                .thenReturn(QUEUE)
                .thenThrow(new IllegalStateException("engine unreachable"));
        when(ai.cacheVerdict(AiOpsMetrics.SYSTEM_USER_ID))
                .thenReturn(CACHE)
                .thenThrow(new IllegalStateException("engine unreachable"));
        AiOpsMetrics metrics = new AiOpsMetrics(ai, registry);

        metrics.refresh();

        assertThat(gauge(AiOpsMetrics.WORKQUEUE_DLQ)).isEqualTo(3.0);
        assertThat(gauge(AiOpsMetrics.CACHE_HIT_RATE)).isEqualTo(0.25);
        assertThat(gauge(AiOpsMetrics.SCRAPE_OK)).isEqualTo(0.0);
    }

    @Test
    void one_endpoint_failing_blanks_only_its_own_half() {
        when(ai.cacheVerdict(AiOpsMetrics.SYSTEM_USER_ID))
                .thenReturn(CACHE)
                .thenThrow(new IllegalStateException("engine unreachable"));
        AiOpsMetrics metrics = new AiOpsMetrics(ai, registry);

        metrics.refresh();

        assertThat(gauge(AiOpsMetrics.WORKQUEUE_DLQ)).isEqualTo(3.0);
        assertThat(gauge(AiOpsMetrics.WORKQUEUE_OK)).isEqualTo(1.0);
        // The queue half still published; the cache half kept its last numbers.
        assertThat(gauge(AiOpsMetrics.CACHE_HIT_RATE)).isEqualTo(0.25);
        assertThat(gauge(AiOpsMetrics.CACHE_ERRORS)).isEqualTo(4.0);
        assertThat(gauge(AiOpsMetrics.SCRAPE_OK)).isEqualTo(0.0);
    }

    @Test
    void an_empty_answer_is_a_failed_read_not_a_healthy_zero() {
        when(ai.workqueueVerdict(AiOpsMetrics.SYSTEM_USER_ID)).thenReturn(QUEUE);
        when(ai.cacheVerdict(AiOpsMetrics.SYSTEM_USER_ID)).thenReturn(Map.of());
        AiOpsMetrics metrics = new AiOpsMetrics(ai, registry);

        // First refresh has an empty cache answer: no cache series may claim a healthy zero.
        assertThat(gauge(AiOpsMetrics.CACHE_HIT_RATE)).isEqualTo(0.0);
        assertThat(gauge(AiOpsMetrics.WORKQUEUE_DLQ)).isEqualTo(3.0);
        assertThat(gauge(AiOpsMetrics.SCRAPE_OK)).isEqualTo(0.0);
    }

    @Test
    void a_later_refresh_replaces_the_readings_together() {
        when(ai.workqueueVerdict(AiOpsMetrics.SYSTEM_USER_ID))
                .thenReturn(QUEUE)
                .thenReturn(Map.of("queue", Map.of("dlq_len", 9, "delayed_len", 0,
                        "pending", 1, "ok", false)));
        AiOpsMetrics metrics = new AiOpsMetrics(ai, registry);

        metrics.refresh();

        assertThat(gauge(AiOpsMetrics.WORKQUEUE_DLQ)).isEqualTo(9.0);
        assertThat(gauge(AiOpsMetrics.WORKQUEUE_DELAYED)).isEqualTo(0.0);
        assertThat(gauge(AiOpsMetrics.WORKQUEUE_OK)).isEqualTo(0.0);
    }

    @Test
    void a_missing_or_malformed_field_degrades_to_zero_for_that_field_only() {
        AiOpsMetrics.Reading r = AiOpsMetrics.project(
                Map.of("queue", Map.of("dlq_len", "not-a-number", "pending", 5, "ok", false)),
                Map.of("cache", Map.of("hit_rate", 0.5)),
                AiOpsMetrics.Reading.empty());

        assertThat(r.workqueueDlq()).isEqualTo(0.0);   // malformed -> 0
        assertThat(r.workqueuePending()).isEqualTo(5.0); // sibling still read
        assertThat(r.workqueueOk()).isEqualTo(0.0);
        assertThat(r.cacheHitRate()).isEqualTo(0.5);
        assertThat(r.cacheErrors()).isEqualTo(0.0);    // absent -> 0
        assertThat(r.scrapeOk()).isEqualTo(1.0);       // both answers present
    }
}
