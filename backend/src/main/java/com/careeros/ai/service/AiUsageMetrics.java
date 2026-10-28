package com.careeros.ai.service;

import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * What the AI has cost in the last day, as a scrape sees it (roadmap 19.9).
 *
 * <p>The ledger is the source of truth: ai-service writes one {@code ai_usage_events} row per
 * call, and the run rollup is derived from that same table, so the number a budget rule alerts
 * on is the number a reader would find in the usage figures -- the scrape does not sum a
 * second, private accounting.
 *
 * <p>The window is a rolling 24 hours rather than a calendar day. A calendar boundary would
 * make the reading jump to zero at midnight UTC and re-arm a budget alert on spend that had
 * not gone away; a rolling window only falls when the calls that produced it age out.
 *
 * <p>A refresh that fails keeps the last reading. A database that is briefly unreachable is
 * not a day that cost nothing, and publishing a zero would silently clear a budget alert at
 * exactly the moment the operator needs it.
 */
@Component
public class AiUsageMetrics {

    /** Micrometer names; the Prometheus exporter renders dots as underscores. */
    static final String COST_24H = "careeros.ai.cost.usd.24h";
    static final String TOKENS_24H = "careeros.ai.tokens.24h";
    static final String CALLS_24H = "careeros.ai.calls.24h";

    /** One query, three readings: a scrape never sees the cost of a different window than the calls. */
    static final String WINDOW_SQL =
            "select coalesce(sum(cost_usd), 0) as cost_usd,"
                    + " coalesce(sum(input_tokens + output_tokens), 0) as tokens,"
                    + " count(*) as calls"
                    + " from ai_usage_events"
                    + " where created_at > now() - interval '24 hours'";

    private static final Logger log = LoggerFactory.getLogger(AiUsageMetrics.class);

    private final JdbcTemplate jdbc;
    private volatile Usage usage = new Usage(0, 0, 0);

    public AiUsageMetrics(JdbcTemplate jdbc, MeterRegistry registry) {
        this.jdbc = jdbc;
        Gauge.builder(COST_24H, this, AiUsageMetrics::costUsd)
                .description("USD spent on AI calls in the trailing 24 hours")
                .register(registry);
        Gauge.builder(TOKENS_24H, this, AiUsageMetrics::tokens)
                .description("Input plus output tokens spent in the trailing 24 hours")
                .register(registry);
        Gauge.builder(CALLS_24H, this, AiUsageMetrics::calls)
                .description("AI calls recorded in the trailing 24 hours")
                .register(registry);
        refresh();
    }

    /** Reads the ledger. Runs on the scheduler's thread, never throws into it. */
    @Scheduled(fixedDelayString = "${careeros.ai.metrics-refresh-ms:60000}")
    public void refresh() {
        try {
            usage = jdbc.queryForObject(WINDOW_SQL, (rs, rowNum) ->
                    new Usage(rs.getDouble("cost_usd"), rs.getLong("tokens"), rs.getLong("calls")));
        } catch (RuntimeException e) {
            log.warn("ai usage metrics could not refresh; the gauges keep their last reading", e);
        }
    }

    private double costUsd() {
        return usage.costUsd();
    }

    private double tokens() {
        return usage.tokens();
    }

    private double calls() {
        return usage.calls();
    }

    /** One row of the window: what the day cost, in money, tokens and calls. */
    record Usage(double costUsd, long tokens, long calls) {
    }
}
