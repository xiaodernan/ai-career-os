package com.careeros.admin;

import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.sql.Timestamp;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;

/**
 * The freshness strip — the closed list of rivers, the ISO instant per row, and the
 * null-quiet case. The cache key is shared with the other admin reads (30s TTL, fail-open).
 */
class AdminFreshnessServiceTest {

    private static AdminCache offCache() {
        return new AdminCache(null, new SimpleMeterRegistry(), new ObjectMapper(), "off", 30);
    }

    @Test
    void answersTheClosedListInOrderAndIsoInstants() {
        Timestamp when = Timestamp.from(java.time.Instant.parse("2026-11-15T08:56:00Z"));
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        when(jdbc.queryForObject(anyString(), eq(Timestamp.class))).thenReturn(when);

        var payload = new AdminFreshnessService(jdbc, offCache()).freshness();

        Object rawFlows = payload.get("flows");
        assertThat(rawFlows).isInstanceOf(List.class);
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> flows = (List<Map<String, Object>>) rawFlows;
        assertThat(flows).hasSize(8);
        assertThat(flows.stream().map(f -> f.get("id"))).containsExactly(
                "users", "applications", "interviewSessions", "agentRuns",
                "aiUsageEvents", "knowledgeSources", "jobMatches", "offers");
        for (Map<String, Object> flow : flows) {
            assertThat(flow).containsEntry("newest", "2026-11-15T08:56:00Z");
            assertThat(flow).containsKeys("table", "newest", "id");
        }
    }

    @Test
    void aQuietTableReadsAsNullNotZeroEpoch() {
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        when(jdbc.queryForObject(anyString(), eq(Timestamp.class))).thenReturn(null);

        var payload = new AdminFreshnessService(jdbc, offCache()).freshness();

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> flows = (List<Map<String, Object>>) payload.get("flows");
        for (Map<String, Object> flow : flows) {
            assertThat(flow.get("newest")).isNull();
        }
    }

    @Test
    void timestampConversionIsTheInstantNotTheLocalZone() {
        Timestamp when = new Timestamp(1_700_000_000_000L);
        assertThat(AdminFreshnessService.timestampToIso(when)).isEqualTo("2023-11-14T22:13:20Z");
        assertThat(AdminFreshnessService.timestampToIso(null)).isNull();
    }
}
