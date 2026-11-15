package com.careeros.admin;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

/**
 * The arithmetic behind the weekly trend lines: the week list is Monday-anchored in UTC,
 * the fill is dense, and out-of-window rows never misalign onto a bucket.
 */
class AdminTrendsServiceTest {

    private static final DateTimeFormatter ISO = DateTimeFormatter.ISO_LOCAL_DATE;

    @Test
    void theWeekListIsAscendingMondaysEndingThisWeek() {
        // a Wednesday, so "this week" cannot be confused for next week's Monday
        LocalDate now = LocalDate.of(2026, 11, 11); // Wednesday
        List<String> weeks = AdminTrends.weeksList(now, 4);
        assertThat(weeks).hasSize(4);
        for (String w : weeks) {
            LocalDate day = LocalDate.parse(w, ISO);
            assertThat(day.getDayOfWeek()).isEqualTo(DayOfWeek.MONDAY);
        }
        assertThat(weeks).isSorted();
        assertThat(weeks.get(3)).isEqualTo(now.with(DayOfWeek.MONDAY).format(ISO));
    }

    @Test
    void theWindowStartIsTheOpeningMondayAtUtcMidnight() {
        LocalDate now = LocalDate.of(2026, 11, 11);
        var start = AdminTrends.windowStart(now, 4);
        var openingMonday = LocalDate.of(2026, 10, 19).atStartOfDay(ZoneOffset.UTC).toInstant();
        assertThat(start).isEqualTo(openingMonday);
        // the wall-clock read of the same instant in UTC is a Monday
        assertThat(LocalDate.ofInstant(start, ZoneId.of("UTC")).getDayOfWeek()).isEqualTo(DayOfWeek.MONDAY);
    }

    @Test
    void fillDensityZeroesQuietWeeksAndIgnoresStrangers() {
        List<String> weeks = List.of("2026-10-19", "2026-10-26", "2026-11-02");
        Map<String, Long> rows = Map.of(
                "2026-10-26", 7L,
                "2026-09-07", 99L); // out of window — must not leak into bucket 0
        assertThat(AdminTrends.fillDensity(weeks, rows)).containsExactly(0L, 7L, 0L);
    }

    @Test
    void fillDensityAnswersZeroForAnEmptyWindow() {
        assertThat(AdminTrends.fillDensity(List.of("2026-11-09"), Map.of())).containsExactly(0L);
    }

    @Test
    void weeksAreClampedToSanity() {
        assertThat(AdminTrends.clampWeeks(0)).isEqualTo(12);
        assertThat(AdminTrends.clampWeeks(-3)).isEqualTo(12);
        assertThat(AdminTrends.clampWeeks(27)).isEqualTo(12);
        assertThat(AdminTrends.clampWeeks(1)).isEqualTo(1);
        assertThat(AdminTrends.clampWeeks(26)).isEqualTo(26);
    }

    @Test
    void foldSkipsRowsMissingParts() {
        List<Map<String, Object>> rows = List.of(
                Map.of("wk", "2026-11-09", "n", 4L),
                new java.util.HashMap<>(), // neither column — a JDBC edge we refuse to miscount
                Map.of("wk", "2026-10-26")); // n absent
        assertThat(AdminTrends.fold(rows)).containsExactly(Map.entry("2026-11-09", 4L));
    }
}
