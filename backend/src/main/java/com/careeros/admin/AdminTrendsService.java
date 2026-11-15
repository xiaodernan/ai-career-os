package com.careeros.admin;

import java.sql.Timestamp;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

/**
 * The install's five weekly series, read off the tables (Epic 251).
 *
 * <p>One query per series — counts only, grouped by ISO week in UTC, lower-bounded by the
 * Monday that opens the requested window. The week list and the dense fill are computed
 * rather than trusted to the database's session timezone, so the answer a browser draws
 * never depends on where the Postgres box sits.
 */
@Service
public class AdminTrendsService {

    /** (table, clock column) pairs — kept as constants so the SQL below has no user input. */
    private static final List<Series> SERIES = List.of(
            new Series("users", "created_at", "users"),
            new Series("applications", "created_at", "applications"),
            new Series("interview_sessions", "started_at", "interviewsPracticed"),
            new Series("agent_runs", "started_at", "agentRuns"),
            new Series("ai_usage_events", "created_at", "aiUsageEvents"));

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
        List<Map<String, Object>> rows = jdbc.queryForList(
                "SELECT to_char(date_trunc('week', " + s.column() + " AT TIME ZONE 'UTC'), 'YYYY-MM-DD') AS wk,"
                        + " count(*) AS n"
                        + " FROM " + s.table()
                        + " WHERE " + s.column() + " >= ?"
                        + " GROUP BY 1",
                Timestamp.from(start));
        return AdminTrends.fillDensity(weeksList, AdminTrends.fold(rows));
    }

    private record Series(String table, String column, String key) {
    }
}
