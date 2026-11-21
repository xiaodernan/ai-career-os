package com.careeros.attention.service;

import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;

/**
 * The overseer's attention view — three counts, one dwell average, twelve paths, no guessing.
 */
class AttentionAdminServiceTest {

    private static AttentionAdminService newService(JdbcTemplate jdbc) {
        return new AttentionAdminService(jdbc, mock(com.careeros.attention.repository.AttentionRepository.class));
    }

    @Test
    void answersEveryCounterWithAZeroWhenTheTablesAreEmpty() {
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        when(jdbc.queryForObject(anyString(), org.mockito.ArgumentMatchers.<Class<Long>>any())).thenReturn(0L);
        when(jdbc.queryForList(anyString())).thenReturn(List.of());

        AttentionAdminService service = newService(jdbc);
        var summary = service.summary();

        assertThat(summary).containsEntry("landings", 0L);
        assertThat(summary).containsEntry("dwells", 0L);
        assertThat(summary).containsEntry("acts", 0L);
        assertThat(summary).containsEntry("bounces", 0L);
        assertThat(summary).containsEntry("bounceRatePct", 0.0);
        assertThat(summary).containsEntry("aimless", 0L);
        assertThat(summary).containsEntry("signedLandings", 0L);
        assertThat(summary).containsEntry("anonymousLandings", 0L);
        assertThat(summary).containsEntry("dwellPerLandingMs", 0L);
        assertThat(summary.get("topLandings")).isInstanceOf(List.class);
        assertThat((List<?>) summary.get("topLandings")).hasSize(0);
    }

    @Test
    void readsThePathRowsAndTheCountsExactlyAsTheyCome() {
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        when(jdbc.queryForObject(anyString(), org.mockito.ArgumentMatchers.<Class<Long>>any())).thenReturn(42L);
        when(jdbc.queryForList(anyString())).thenReturn(List.of(
                Map.of("path", "/dashboard", "landings", 100L, "dwells", 85L, "acts", 20L)));

        AttentionAdminService service = newService(jdbc);
        var summary = service.summary();

        assertThat(summary).containsEntry("landings", 42L);
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> paths = (List<Map<String, Object>>) summary.get("topLandings");
        assertThat(paths).hasSize(1);
        assertThat(paths.get(0)).containsEntry("path", "/dashboard");
    }
}
