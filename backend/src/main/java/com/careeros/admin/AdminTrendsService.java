package com.careeros.admin;

import java.sql.Timestamp;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

/**
 * The install's weekly series, read off the tables (Epic 251; attention heartbeat, Epic 279).
 *
 * <p>One query per series — counts only, grouped by ISO week in UTC, lower-bounded by the
 * Monday that opens the requested window. The week list and the dense fill are computed
 * rather than trusted to the database's session timezone, so the answer a browser draws
 * never depends on where the Postgres box sits.
 */
@Service
public class AdminTrendsService {

    /**
     * (table, clock column, wire key, constant filter) tuples — kept as constants so the SQL
     * below has no user input. The filter is spliced as a constant, never as a parameter: this
     * service takes no query text. An empty/null filter means the table's own count.
     */
    private static final List<Series> SERIES = List.of(
            new Series("users", "created_at", "users", null),
            new Series("applications", "created_at", "applications", null),
            new Series("interview_sessions", "started_at", "interviewsPracticed", null),
            new Series("agent_runs", "started_at", "agentRuns", null),
            new Series("ai_usage_events", "created_at", "aiUsageEvents", null),
    // The weekly install window (Epic 279): the attention ledger's heartbeat as two steady lines.
    // The third kind (`act`) is written since Epic 283 (the landing's Start-free CTA) and Epic
    // 289 (the overseer's synthetic door) — it stays out of the weekly frame because a sparse
    // series reads worse than silence, and the trailing-30-day door counts the number.
    new Series("attention_events", "created_at", "attentionLands", "event = 'land'"),
    new Series("attention_events", "created_at", "attentionDwells", "event = 'dwell'"),
    // The Monday letter (Epics 251/305): every row in weekly_digests is a letter the backend
    // attempted to compose that week; delivered_at IS NOT NULL marks the ones that actually went
    // out. attempts − delivered is the refusal rate the install wears — a number not inferred from
    // counters inside one JVM, but read straight off the rows.
    new Series("weekly_digests", "week_start::timestamp", "weeklyDigests", null),
    new Series("weekly_digests", "week_start::timestamp", "weeklyDigestsDelivered",
            "delivered_at IS NOT NULL"));

    private final JdbcTemplate jdbc;
    private final AdminCache cache;

    public AdminTrendsService(JdbcTemplate jdbc, AdminCache cache) {
        this.jdbc = jdbc;
        this.cache = cache;
    }

    /** The full trend payload: the shared week list plus one dense array per series. */
    public Map<String, Object> trends(int weeks) {
        int span = AdminTrends.clampWeeks(weeks);
        // five aggregates the page re-polls; a 30-second window of staleness is honest here (Epic 253)
        return cache.get("trends:" + span).orElseGet(() -> {
            LocalDate now = LocalDate.now(ZoneOffset.UTC);
            List<String> weeksList = AdminTrends.weeksList(now, span);
            var start = AdminTrends.windowStart(now, span);

            Map<String, List<Long>> series = new java.util.LinkedHashMap<>();
            for (Series s : SERIES) {
                series.put(s.key(), dense(s, start, weeksList));
            }

            Map<String, Object> out = new java.util.LinkedHashMap<>();
            out.put("weeks", weeksList);
            out.put("series", series);
            out.put("weeksRequested", span);
            cache.put("trends:" + span, out);
            return out;
        });
    }

    private List<Long> dense(Series s, java.time.Instant start, List<String> weeksList) {
        // the filter is a compile-time constant from SERIES above — never a user-controlled value
        String filter = s.where() == null ? "" : " AND " + s.where();
        List<Map<String, Object>> rows = jdbc.queryForList(
                "SELECT to_char(date_trunc('week', " + s.column() + " AT TIME ZONE 'UTC'), 'YYYY-MM-DD') AS wk,"
                        + " count(*) AS n"
                        + " FROM " + s.table()
                        + " WHERE " + s.column() + " >= ?" + filter
                        + " GROUP BY 1",
                Timestamp.from(start));
        return AdminTrends.fillDensity(weeksList, AdminTrends.fold(rows));
    }

    private record Series(String table, String column, String key, String where) {
    }
}
