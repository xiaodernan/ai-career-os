package com.careeros.attention.service;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

/**
 * The admin view over the attention rows (Epic 267).
 *
 * <p>Twenty numbers, one question per side: how are readers behaving, and is this a page
 * worth keeping. Counts and averages only — never a per-reader row. Inputs arrive the
 * way the browser sends them (path + event + optional value), stored and counted.
 */
@Service
public class AttentionAdminService {

    private static final int DEFAULT_DAYS = 30;

    private final JdbcTemplate jdbc;

    public AttentionAdminService(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public Map<String, Object> summary() {
        int days = DEFAULT_DAYS;
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("days", days);
        out.put("landings", one("SELECT count(*) FROM attention_events WHERE event='land' AND created_at >= now() - interval '" + days + " days'"));
        out.put("dwells",   one("SELECT count(*) FROM attention_events WHERE event='dwell' AND created_at >= now() - interval '" + days + " days'"));
        out.put("acts",     one("SELECT count(*) FROM attention_events WHERE event='act' AND created_at >= now() - interval '" + days + " days'"));
        out.put("signedLandings",    one("SELECT count(*) FROM attention_events WHERE event='land' AND user_id IS NOT NULL AND created_at >= now() - interval '" + days + " days'"));
        out.put("anonymousLandings", one("SELECT count(*) FROM attention_events WHERE event='land' AND user_id IS NULL AND created_at >= now() - interval '" + days + " days'"));

        long dwellMs = 0L;
        Long avg = jdbc.queryForObject(
            "SELECT coalesce(avg((value)::bigint), 0) FROM attention_events WHERE event='dwell' AND value ~ '^[0-9]+$'"
                + " AND created_at >= now() - interval '" + days + " days'",
            Long.class);
        dwellMs = avg == null ? 0L : avg;
        out.put("dwellPerLandingMs", dwellMs);

        List<Map<String, Object>> topLandings = jdbc.queryForList(
            "SELECT path, count(*) FILTER (WHERE event='land') AS landings,"
                    + " count(*) FILTER (WHERE event='dwell') AS dwells,"
                    + " count(*) FILTER (WHERE event='act') AS acts"
                    + " FROM attention_events"
                    + " WHERE created_at >= now() - interval '" + days + " days'"
                    + "   AND path NOT LIKE '/admin%'"
                    + " GROUP BY path ORDER BY landings DESC LIMIT 12");
        out.put("topLandings", topLandings);
        return out;
    }

    private long one(String sql) {
        Long n = jdbc.queryForObject(sql, Long.class);
        return n == null ? 0L : n;
    }
}
