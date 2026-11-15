package com.careeros.admin;

import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;

/**
 * The quiet cohort — dense week list, registered/active pairs, and a quiet week reading as
 * two zeros rather than a missing row.
 */
class AdminCohortServiceTest {

    private static AdminCache offCache() {
        return new AdminCache(null, new SimpleMeterRegistry(), new ObjectMapper(), "off", 30);
    }

    @Test
    void theCohortAnswersDenseRowsWithZerosForQuietWeeks() {
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        List<Map<String, Object>> rows = List.of(
                Map.of("wk", "2026-11-09", "registered", 5L, "active", 3L),
                Map.of("wk", "2026-10-26", "registered", 7L, "active", 2L));
        when(jdbc.queryForList(anyString(), org.mockito.ArgumentMatchers.<Timestamp>any())).thenReturn(rows);

        var payload = new AdminCohortService(jdbc, offCache()).cohort(12);

        assertThat(payload).containsEntry("weeksRequested", 12);
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> cohort = (List<Map<String, Object>>) payload.get("cohort");
        assertThat(cohort).hasSize(12);
        for (Map<String, Object> row : cohort) {
            assertThat(row).containsKeys("week", "registered", "active");
        }
        // the list is descending in insertion order (oldest first); only weeks present in
        // the fixture carry non-zero numbers
        long totalRegistered = cohort.stream().mapToLong(r -> (Long) r.get("registered")).sum();
        assertThat(totalRegistered).isEqualTo(12L);
    }

    @Test
    void weeksAreClampedToTheTwoBoundaries() {
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        when(jdbc.queryForList(anyString(), org.mockito.ArgumentMatchers.<Timestamp>any())).thenReturn(List.of());

        assertThat(((List<?>) new AdminCohortService(jdbc, offCache()).cohort(0).get("weeks")))
                .hasSize(12);
        assertThat(((List<?>) new AdminCohortService(jdbc, offCache()).cohort(40).get("weeks")))
                .hasSize(12);
        assertThat(((List<?>) new AdminCohortService(jdbc, offCache()).cohort(6).get("weeks")))
                .hasSize(6);
    }
}
