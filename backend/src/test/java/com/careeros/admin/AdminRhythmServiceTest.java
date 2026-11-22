package com.careeros.admin;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.sql.Timestamp;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;

/**
 * The rhythm's arithmetic: seven days by twenty-four hours, dense, additive when
 * Postgres returns overlapping buckets, and blind to anything malformed.
 */
class AdminRhythmServiceTest {

    private static AdminCache offCache() {
        return new AdminCache(null, new SimpleMeterRegistry(), new ObjectMapper(), "off", 30);
    }

    @Test
    void aQuietLedgerAnswersAFullGridOfZeros() {
        var grid = AdminRhythmService.fold(List.of());
        assertThat(grid.cells()).hasSize(7);
        assertThat(grid.cells()).allSatisfy(row -> {
            assertThat(row).hasSize(24);
            assertThat(row).allMatch(value -> value == 0L);
        });
        assertThat(grid.total()).isZero();
        assertThat(grid.peak()).isZero();
    }

    @Test
    void bucketsAddUpAndThePeakIsTheBusiestCell() {
        var grid = AdminRhythmService.fold(List.of(
                Map.of("dow", 1, "hr", 9, "n", 12L),
                Map.of("dow", 1, "hr", 9, "n", 5L),
                Map.of("dow", 3, "hr", 20, "n", 19L)));
        assertThat(grid.cells().get(1).get(9)).isEqualTo(17L);
        assertThat(grid.cells().get(3).get(20)).isEqualTo(19L);
        assertThat(grid.total()).isEqualTo(36L);
        assertThat(grid.peakDow()).isEqualTo(3);
        assertThat(grid.peakHour()).isEqualTo(20);
        assertThat(grid.peak()).isEqualTo(19L);
    }

    @Test
    void malformedAndOutOfRangeRowsAreSkippedRatherThanThrown() {
        var grid = AdminRhythmService.fold(List.of(
                Map.of("dow", 7, "hr", 9, "n", 3L),
                Map.of("dow", 2, "hr", 24, "n", 4L),
                Map.of("dow", 2, "hr", 10, "n", -1L),
                Map.of("dow", "Tuesday", "hr", 10, "n", 6L),
                Map.of("dow", 2, "hr", 10)));
        assertThat(grid.total()).isZero();
        assertThat(grid.cells().get(2).get(10)).isZero();
    }

    @Test
    void theWindowIsClampedToAUsefulRange() {
        assertThat(AdminRhythmService.clampWindow(0)).isEqualTo(28);
        assertThat(AdminRhythmService.clampWindow(3)).isEqualTo(7);
        assertThat(AdminRhythmService.clampWindow(30)).isEqualTo(30);
        assertThat(AdminRhythmService.clampWindow(365)).isEqualTo(84);
    }

    @Test
    void thePayloadSaysWhatItMeasuredAndWhereThePeakSits() {
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        when(jdbc.queryForList(anyString(), any(Timestamp.class)))
                .thenReturn(List.of(Map.of("dow", 5, "hr", 8, "n", 21L)));

        Map<String, Object> payload = new AdminRhythmService(jdbc, offCache()).rhythm(28);

        assertThat(payload).containsEntry("days", 7);
        assertThat(payload).containsEntry("hours", 24);
        assertThat(payload).containsEntry("windowDays", 28);
        assertThat(payload).containsEntry("timezone", "UTC");
        assertThat(payload).containsEntry("total", 21L);
        @SuppressWarnings("unchecked")
        List<List<Long>> cells = (List<List<Long>>) payload.get("cells");
        assertThat(cells).hasSize(7);
        assertThat(cells.get(5).get(8)).isEqualTo(21L);
        @SuppressWarnings("unchecked")
        Map<String, Object> peak = (Map<String, Object>) payload.get("peak");
        assertThat(peak).containsEntry("dow", 5).containsEntry("hour", 8).containsEntry("n", 21L);
    }
}
