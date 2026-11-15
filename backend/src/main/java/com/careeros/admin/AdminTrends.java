package com.careeros.admin;

import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.time.DayOfWeek;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * The five weekly series the overseer watches, and the arithmetic behind them.
 *
 * <p>Everything in this class is a read of the install's own rows bucketed by ISO week
 * (Monday start, UTC). No fixture, no estimate, no market data — the shape a reader sees
 * on /admin is the shape the tables actually hold.
 *
 * <p>Week 0 of {@link #weeksList} is the week that contains today; the list is oldest
 * first so a sparkline draws left-to-right in time order.
 */
final class AdminTrends {

    static final DateTimeFormatter ISO = DateTimeFormatter.ISO_LOCAL_DATE;

    private AdminTrends() {
    }

    /** Clamp to [1, 26]; a nonsensical request answers with the default window. */
    static int clampWeeks(int weeks) {
        if (weeks < 1 || weeks > 26) {
            return 12;
        }
        return weeks;
    }

    /** ISO week-start Mondays, oldest first, ending with the Monday of the current week. */
    static List<String> weeksList(LocalDate now, int weeks) {
        LocalDate monday = now.with(DayOfWeek.MONDAY);
        LocalDate first = monday.minusWeeks(weeks - 1L);
        List<String> out = new ArrayList<>(weeks);
        for (int i = 0; i < weeks; i++) {
            out.add(first.plusWeeks(i).format(ISO));
        }
        return out;
    }

    /** The instant of the Monday that opens the window — the query's own lower bound. */
    static Instant windowStart(LocalDate now, int weeks) {
        LocalDate monday = now.with(DayOfWeek.MONDAY);
        return monday.minusWeeks(weeks - 1L).atStartOfDay(ZoneOffset.UTC).toInstant();
    }

    /**
     * Align a sparse {week, count} map onto the full week list. Weeks with no rows read as
     * zero — a quiet week is a fact, not a missing key — and rows outside the window are
     * ignored rather than misaligned.
     */
    static List<Long> fillDensity(List<String> weeks, Map<String, Long> rows) {
        List<Long> out = new ArrayList<>(weeks.size());
        for (String week : weeks) {
            out.add(rows.getOrDefault(week, 0L));
        }
        return out;
    }

    /** Fold the JDBC row shape into week -> count. */
    static Map<String, Long> fold(List<Map<String, Object>> rows) {
        Map<String, Long> byWeek = new HashMap<>();
        for (Map<String, Object> row : rows) {
            Object wk = row.get("wk");
            Object n = row.get("n");
            if (wk == null || n == null) {
                continue;
            }
            Number count = (Number) n;
            byWeek.put(wk.toString(), count.longValue());
        }
        return byWeek;
    }
}
