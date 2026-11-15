package com.careeros.admin;

import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;

/**
 * The funnel — stage order is part of the contract, distinct readers are the only
 * number it may emit, and a quiet table reads as zero, never as a missing stage.
 */
class AdminFunnelServiceTest {

    private static AdminCache offCache() {
        return new AdminCache(null, new SimpleMeterRegistry(), new ObjectMapper(), "off", 30);
    }

    @Test
    void theSixStagesAnswerInOrderAndMatchedIsTheSideSignal() {
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        when(jdbc.queryForObject(anyString(), eq(Long.class)))
                .thenReturn(6655L, 1543L, 610L, 345L, 20L, 264L);

        var payload = new AdminFunnelService(jdbc, offCache()).funnel();

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> stages = (List<Map<String, Object>>) payload.get("stages");
        assertThat(stages).hasSize(5);
        assertThat(stages.stream().map(s -> s.get("id")))
                .containsExactly("registered", "uploaded", "applied", "interviewed", "offered");
        assertThat(stages.stream().map(s -> s.get("readers")))
                .containsExactly(6655L, 1543L, 610L, 345L, 20L);
        assertThat(payload).containsEntry("matchedReaders", 264L);
    }

    @Test
    void aQuietTableReadsAsZeroNotAsAMissingStage() {
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        when(jdbc.queryForObject(anyString(), eq(Long.class))).thenReturn(null);

        var payload = new AdminFunnelService(jdbc, offCache()).funnel();

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> stages = (List<Map<String, Object>>) payload.get("stages");
        for (Map<String, Object> stage : stages) {
            assertThat(stage).containsEntry("readers", 0L);
        }
        assertThat(payload).containsEntry("matchedReaders", 0L);
    }
}
