package com.careeros.admin;

import java.util.List;
import java.util.Map;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * The seven-day cache ledger, straight off the table (Epic 318).
 *
 * <p>{@code ai_usage_events} already carries the truth every provider call leaves behind:
 * tokens in, tokens cached, the kind it rode in on. The overseer reading the admin page
 * kept asking "is the cache actually working?" — the top-of-page trends answer volume,
 * not warmth. This route answers warmth: rows per kind for the trailing 7 days, plus the
 * install total, all summed from the raw events (never an average of per-row ratios,
 * which would let a tiny hot call fan in with a giant cold one and read pretty).
 *
 * <p>Counts-only, like every other admin route: no user rows, no payloads, no prompt
 * text, no model output. The by-kind rows are the wire's own vocabulary (the kinds the
 * engine writes: {@code step_1..step_3}, {@code jd_analyze}, {@code answer_eval}, …).
 */
@RestController
@RequestMapping("/api/v1/admin")
public class AdminCacheEconomyController {

    private static final String WINDOW_DAYS = "7";

    private final JdbcTemplate jdbc;
    private final AdminCache cache;

    public AdminCacheEconomyController(JdbcTemplate jdbc, AdminCache cache) {
        this.jdbc = jdbc;
        this.cache = cache;
    }

    @GetMapping("/cache-economy")
    public Map<String, Object> cacheEconomy() {
        return cache.get("cache-economy").orElseGet(() -> {
            List<Map<String, Object>> byKind = jdbc.queryForList(
                    "SELECT kind,\n"
                            + "       count(*) AS calls,\n"
                            + "       sum(input_tokens) AS input_tokens,\n"
                            + "       sum(cached_tokens) AS cached_tokens,\n"
                            + "       round(100.0 * sum(cached_tokens) / nullif(sum(input_tokens), 0), 1) AS hit_pct\n"
                            + "FROM ai_usage_events\n"
                            + "WHERE created_at > now() - interval '" + WINDOW_DAYS + " days'\n"
                            + "GROUP BY kind\n"
                            + "ORDER BY calls DESC\n"
                            + "LIMIT 25");
            Map<String, Object> totals = jdbc.queryForMap(
                    "SELECT count(*) AS calls,\n"
                            + "       sum(input_tokens) AS input_tokens,\n"
                            + "       sum(cached_tokens) AS cached_tokens,\n"
                            + "       round(100.0 * sum(cached_tokens) / nullif(sum(input_tokens), 0), 1) AS hit_pct\n"
                            + "FROM ai_usage_events\n"
                            + "WHERE created_at > now() - interval '" + WINDOW_DAYS + " days'");
            Map<String, Object> out = new java.util.LinkedHashMap<>();
            out.put("windowDays", Long.parseLong(WINDOW_DAYS));
            out.put("totals", totals);
            out.put("byKind", byKind);
            cache.put("cache-economy", out);
            return out;
        });
    }
}
