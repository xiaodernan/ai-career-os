package com.careeros.admin;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.data.redis.core.StringRedisTemplate;

/**
 * The operator's cache — mode parsing fails closed, off passes through byte for byte,
 * a caffeine hit round-trips, and a JSON tree re-reads every narrow integer as a Long.
 */
class AdminCacheTest {

    private AdminCache cache(String mode, long ttl) {
        return new AdminCache(mock(StringRedisTemplate.class), new SimpleMeterRegistry(),
                new ObjectMapper(), mode, ttl);
    }

    @Test
    void unknownSpellingFailsClosedToOff() {
        assertThat(cache("rediss!", 30).mode()).isEqualTo("off");
        assertThat(cache("FALSE", 30).mode()).isEqualTo("off");
        assertThat(cache("0", 30).mode()).isEqualTo("off");
        assertThat(cache("caffeine", 30).mode()).isEqualTo("caffeine");
        assertThat(cache("redis", 30).mode()).isEqualTo("redis");
    }

    @Test
    void offModeNeverTouchesRedisAndAlwaysMisses() {
        // a null template is fine here — the off branch short-circuits before any redis call
        AdminCache off = new AdminCache(null, new SimpleMeterRegistry(), new ObjectMapper(), "off", 30);
        assertThat(off.get("stats")).isEmpty();
        assertThat(off.mode()).isEqualTo("off");
    }

    @Test
    void caffeineRoundTripsAPayloadAndIsolatesKeys() {
        AdminCache cache = cache("caffeine", 30);
        Map<String, Object> stats = Map.of("users", 7L, "jobs", 3L);
        cache.put("stats", stats);
        assertThat(cache.get("stats")).isPresent();
        assertThat(cache.get("stats").get()).containsEntry("users", 7L);
        assertThat(cache.get("trends:12")).isEmpty();
    }

    @Test
    void deepNormalizeWidensEveryIntegerInsideTheTree() {
        Map<String, Object> nested = Map.of(
                "weeks", List.of("2026-11-09"),
                "series", Map.of(
                        "users", List.of(0, 7, 1933)));
        @SuppressWarnings("unchecked")
        Map<String, Object> out = (Map<String, Object>) AdminCache.deepNormalize(nested);
        @SuppressWarnings("unchecked")
        List<Object> users = (List<Object>) ((Map<String, Object>) out.get("series")).get("users");
        assertThat(users).containsExactly(0L, 7L, 1933L);
        assertThat(out.get("weeks")).isEqualTo(List.of("2026-11-09"));
    }

    @Test
    void jitterStaysInsideTheBand() {
        java.util.Random seeded = new java.util.Random(42);
        for (int i = 0; i < 200; i++) {
            long jittered = AdminCache.jitterSeconds(30, seeded);
            assertThat(jittered).isBetween(27L, 33L);
        }
        // a floor at 1s keeps a tiny base from jittering to zero
        assertThat(AdminCache.jitterSeconds(1, seeded)).isBetween(1L, 2L);
    }
}
