package com.careeros.admin;

import java.sql.Timestamp;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

/**
 * The install's behavioural rhythm (Epic 383): when readers arrive, bucketed by
 * UTC day-of-week and hour over a rolling window.
 *
 * <p>The weekly trend line answers "is the door busier than last week"; it cannot
 * answer "at which hour is it busiest", because a week is the finest bucket it
 * keeps. This view adds the missing resolution without adding a row of personal
 * data: the query counts `attention_events` landings and nothing else, and the
 * grid is dense so a quiet hour reads as zero rather than a missing cell.
 *
 * <p>UTC on purpose: the page converts to the reader's own clock, which is the
 * only timezone the operator can reason about without trusting the database
 * box's locale. The wire says so explicitly.
 */
@Service
public class AdminRhythmService {

    static final int DAYS = 7;
    static final int HOURS = 24;
    static final int DEFAULT_WINDOW = 28;
    static final int MAX_WINDOW = 84;

    private static final String SQL =
            "SELECT EXTRACT(DOW FROM created_at AT TIME ZONE 'UTC')::int AS dow,"
                    + " EXTRACT(HOUR FROM created_at AT TIME ZONE 'UTC')::int AS hr,"
                    + " count(*) AS n"
                    + " FROM attention_events"
                    + " WHERE event = 'land' AND created_at >= ?"
                    + " GROUP BY 1, 2";

    private final JdbcTemplate jdbc;
    private final AdminCache cache;

    public AdminRhythmService(JdbcTemplate jdbc, AdminCache cache) {
        this.jdbc = jdbc;
        this.cache = cache;
    }

    public Map<String, Object> rhythm(int days) {
        int span = clampWindow(days);
        return cache.get("rhythm:" + span).orElseGet(() -> {
            Instant start = Instant.now().minus(span, ChronoUnit.DAYS);
            List<Map<String, Object>> rows = jdbc.queryForList(SQL, Timestamp.from(start));
            Grid grid = fold(rows);
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("days", DAYS);
            out.put("hours", HOURS);
            out.put("windowDays", span);
            out.put("timezone", "UTC");
            out.put("total", grid.total());
            out.put("cells", grid.cells());
            out.put("peak", Map.of("dow", grid.peakDow(), "hour", grid.peakHour(), "n", grid.peak()));
            cache.put("rhythm:" + span, out);
            return out;
        });
    }

    static int clampWindow(int days) {
        if (days <= 0) {
            return DEFAULT_WINDOW;
        }
        return Math.min(MAX_WINDOW, Math.max(DAYS, days));
    }

    /** A dense 7×24 grid; rows are Sunday..Saturday, matching Postgres `DOW`. */
    static Grid fold(List<Map<String, Object>> rows) {
        long[][] cells = new long[DAYS][HOURS];
        long total = 0;
        int peakDow = 0;
        int peakHour = 0;
        long peak = 0;
        for (Map<String, Object> row : rows) {
            Integer dow = asInt(row.get("dow"));
            Integer hour = asInt(row.get("hr"));
            Long count = asLong(row.get("n"));
            // A malformed row is skipped rather than thrown: one bad bucket must not
            // take the whole rhythm down, and a missing cell already means "no data".
            if (dow == null || hour == null || count == null || dow < 0 || dow >= DAYS
                    || hour < 0 || hour >= HOURS || count < 0) {
                continue;
            }
            cells[dow][hour] += count;
            total += count;
            if (cells[dow][hour] > peak) {
                peak = cells[dow][hour];
                peakDow = dow;
                peakHour = hour;
            }
        }
        List<List<Long>> wire = new ArrayList<>(DAYS);
        for (long[] day : cells) {
            List<Long> line = new ArrayList<>(HOURS);
            for (long value : day) {
                line.add(value);
            }
            wire.add(List.copyOf(line));
        }
        return new Grid(List.copyOf(wire), total, peakDow, peakHour, peak);
    }

    private static Integer asInt(Object value) {
        return value instanceof Number number ? number.intValue() : null;
    }

    private static Long asLong(Object value) {
        return value instanceof Number number ? number.longValue() : null;
    }

    record Grid(List<List<Long>> cells, long total, int peakDow, int peakHour, long peak) {
    }
}
