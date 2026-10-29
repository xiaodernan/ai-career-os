package com.careeros.ai.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;

/**
 * The AI budget as Prometheus reads it (roadmap 19.9).
 *
 * <p>The gauges are a cache of the ledger's last answer, and these cases pin the two
 * things a cache can get wrong. A refresh publishes all three readings from one row --
 * cost, tokens and calls cannot come from different windows. A refresh that fails keeps
 * the last good reading: a database that is briefly unreachable must not publish a zero
 * and silently clear the budget alert.
 */
@SuppressWarnings("unchecked")
class AiUsageMetricsTest {

    private SimpleMeterRegistry registry;
    private JdbcTemplate jdbc;
    /** Micrometer holds the gauge's object weakly; a field keeps it alive across the read. */
    private AiUsageMetrics constructed;

    @BeforeEach
    void setUp() {
        registry = new SimpleMeterRegistry();
        jdbc = mock(JdbcTemplate.class);
    }

    private void answer(AiUsageMetrics.Usage usage) {
        when(jdbc.queryForObject(eq(AiUsageMetrics.WINDOW_SQL), any(RowMapper.class)))
                .thenReturn(usage);
    }

    private double gauge(String name) {
        return registry.get(name).gauge().value();
    }

    @Test
    void the_first_read_publishes_the_ledgers_window() {
        answer(new AiUsageMetrics.Usage(1.25, 3400, 12));

        constructed = new AiUsageMetrics(jdbc, registry);

        assertThat(gauge(AiUsageMetrics.COST_24H)).isEqualTo(1.25);
        assertThat(gauge(AiUsageMetrics.TOKENS_24H)).isEqualTo(3400.0);
        assertThat(gauge(AiUsageMetrics.CALLS_24H)).isEqualTo(12.0);
    }

    @Test
    void a_later_refresh_replaces_all_three_readings_together() {
        when(jdbc.queryForObject(eq(AiUsageMetrics.WINDOW_SQL), any(RowMapper.class)))
                .thenReturn(new AiUsageMetrics.Usage(1.0, 100, 2))
                .thenReturn(new AiUsageMetrics.Usage(2.5, 900, 7));
        AiUsageMetrics metrics = new AiUsageMetrics(jdbc, registry);

        metrics.refresh();

        assertThat(gauge(AiUsageMetrics.COST_24H)).isEqualTo(2.5);
        assertThat(gauge(AiUsageMetrics.TOKENS_24H)).isEqualTo(900.0);
        assertThat(gauge(AiUsageMetrics.CALLS_24H)).isEqualTo(7.0);
    }

    @Test
    void a_failed_refresh_keeps_the_last_good_reading_rather_than_publishing_zero() {
        when(jdbc.queryForObject(eq(AiUsageMetrics.WINDOW_SQL), any(RowMapper.class)))
                .thenReturn(new AiUsageMetrics.Usage(2.0, 500, 4))
                .thenThrow(new IllegalStateException("db down"));
        AiUsageMetrics metrics = new AiUsageMetrics(jdbc, registry);

        metrics.refresh();

        assertThat(gauge(AiUsageMetrics.COST_24H)).isEqualTo(2.0);
        assertThat(gauge(AiUsageMetrics.TOKENS_24H)).isEqualTo(500.0);
        assertThat(gauge(AiUsageMetrics.CALLS_24H)).isEqualTo(4.0);
    }
}
