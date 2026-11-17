package com.careeros.admin;

import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import com.fasterxml.jackson.databind.ObjectMapper;

/**
 * The cache economy — sums come straight off the rows, never an average of ratios.
 * The by-kind rollup and the totals are two separate reads of the same table:
 * an average of per-row hit rates would lie whenever a huge cold row sits next
 * to a tiny hot one.
 */
class AdminCacheEconomyControllerTest {

    private static AdminCache offCache() {
        return new AdminCache(null, new SimpleMeterRegistry(), new ObjectMapper(), "off", 30);
    }

    private static Map<String, Object> row(Object... kvs) {
        Map<String, Object> row = new java.util.HashMap<>();
        for (int i = 0; i < kvs.length; i += 2) {
            row.put((String) kvs[i], kvs[i + 1]);
        }
        return row;
    }

    @Test
    void theTotalsComeFromOneSumNotAnAverageOfRows() {
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        List<Map<String, Object>> byKind = List.of(
                row("kind", "step_1", "calls", 174L, "input_tokens", 604204L,
                        "cached_tokens", 188800L, "hit_pct", 31.2),
                row("kind", "resume_parse", "calls", 316L, "input_tokens", 850541L,
                        "cached_tokens", 716934L, "hit_pct", 84.3));
        when(jdbc.queryForList(anyString())).thenReturn(byKind);
        when(jdbc.queryForMap(anyString())).thenReturn(
                row("calls", 490L, "input_tokens", 1454745L, "cached_tokens", 905734L,
                        "hit_pct", 62.2));

        AdminCacheEconomyController controller = new AdminCacheEconomyController(jdbc, offCache());
        var out = controller.cacheEconomy();

        assertThat(out.get("windowDays")).isEqualTo(7L);
        assertThat(((Map<String, Object>) out.get("totals")).get("hit_pct")).isEqualTo(62.2);
        var kinds = (List<Map<String, Object>>) out.get("byKind");
        assertThat(kinds).hasSize(2);
        assertThat(kinds.get(0).get("kind")).isEqualTo("step_1");
        assertThat(kinds.get(1).get("hit_pct")).isEqualTo(84.3);
    }

    @Test
    void aNullHitPctRidesThroughAsNullNeverInventedZero() {
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        when(jdbc.queryForList(anyString())).thenReturn(List.of(
                row("kind", "quiet", "calls", 1L, "input_tokens", 0L,
                        "cached_tokens", 0L, "hit_pct", null)));
        when(jdbc.queryForMap(anyString())).thenReturn(
                row("calls", 1L, "input_tokens", 0L, "cached_tokens", 0L, "hit_pct", null));

        AdminCacheEconomyController controller = new AdminCacheEconomyController(jdbc, offCache());
        var out = controller.cacheEconomy();

        assertThat(((Map<String, Object>) out.get("totals")).get("hit_pct")).isNull();
        var kinds = (List<Map<String, Object>>) out.get("byKind");
        assertThat(kinds.get(0).get("hit_pct")).isNull();
    }
}
