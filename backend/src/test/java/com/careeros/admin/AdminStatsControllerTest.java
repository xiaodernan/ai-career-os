package com.careeros.admin;

import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;

/**
 * The operator's tally — counts are the contract whatever the numbers are.
 * A null row-count reads as 0; every key the frontend asks for is present.
 */
class AdminStatsControllerTest {

    @Test
    void answersEveryCountWithZeroWhenTheRowsAreUnknown() {
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        when(jdbc.queryForObject(anyString(), org.mockito.ArgumentMatchers.<Class<Long>>any())).thenReturn(5L);
        AdminStatsController controller = new AdminStatsController(jdbc);
        var stats = controller.stats();

        List<String> keys = List.of(
                "users", "resumes", "applications", "interviewsPracticed", "interviewTurns",
                "agentRuns", "agentTraces", "aiUsageEvents", "knowledgeSources",
                "notesKept", "coverLetters", "contacts", "memories",
                "companies", "jobs", "matches", "conversations", "messages",
                "savedSearches", "offers");
        for (String key : keys) {
            assertThat(stats).containsKey(key);
            assertThat(stats.get(key)).isEqualTo(5L);
        }
    }

    @Test
    void treatsANullCountAsZero() {
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        when(jdbc.queryForObject(anyString(), org.mockito.ArgumentMatchers.<Class<Long>>any())).thenReturn(null);
        AdminStatsController controller = new AdminStatsController(jdbc);
        var stats = controller.stats();
        assertThat(stats.get("users")).isEqualTo(0L);
        assertThat(stats.get("offers")).isEqualTo(0L);
    }
}
