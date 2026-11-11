package com.careeros.report.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.careeros.report.dto.DashboardDtos.DashboardResponse;
import com.careeros.report.dto.DashboardDtos.Kanban;
import com.careeros.report.dto.DashboardDtos.RecentActivity;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.time.Duration;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;

/**
 * The dashboard read-through cache (Epic 125), pinned without a running Redis.
 *
 * <p>Three backends, one contract: <b>off</b> never serves, <b>caffeine</b> serves
 * what it stored until the TTL, <b>redis</b> is fail-open -- an outage is a miss, and
 * a poisoned entry is evicted rather than pinned. Live-Redis behaviour (the actual
 * socket, the actual TTL propagation) is not claimed here; that is the same posture
 * as the rate limiter's own suite, which pins the fallback arithmetic and leaves the
 * round-trip to the deployment.
 */
class DashboardCacheTest {

    private StringRedisTemplate redis;
    private ValueOperations<String, String> ops;
    private SimpleMeterRegistry registry;
    private ObjectMapper mapper;

    @BeforeEach
    void setUp() {
        redis = mock(StringRedisTemplate.class);
        ops = mock(ValueOperations.class);
        when(redis.opsForValue()).thenReturn(ops);
        registry = new SimpleMeterRegistry();
        mapper = new ObjectMapper().findAndRegisterModules();
    }

    private DashboardResponse sample() {
        return new DashboardResponse(
                new Kanban(Map.of("applied", 2L), 2, 0),
                1L,
                0.75f,
                1,
                List.of(),
                List.of(),
                null,
                null,
                List.of(),
                List.of(),
                List.of(new RecentActivity(UUID.randomUUID(), UUID.randomUUID(), "applied",
                        Map.of("job", "acme", "count", 1L),
                        OffsetDateTime.of(2026, 11, 11, 12, 0, 0, 0, ZoneOffset.UTC))));
    }

    private DashboardCache cache(String mode, long ttlSeconds) {
        return new DashboardCache(redis, registry, mapper, mode, ttlSeconds);
    }

    @Test
    void offNeverServesAndNeverWrites() throws Exception {
        DashboardResponse built = sample();
        DashboardCache cache = cache("off", 45);

        assertThat(cache.get(UUID.randomUUID())).isEmpty();
        cache.put(UUID.randomUUID(), built);

        assertThatCode(() -> cache.put(UUID.randomUUID(), built)).doesNotThrowAnyException();
        // off is passthrough: the redis side of the world was never touched.
        verify(ops, times(0)).set(anyString(), anyString(), any(Duration.class));
    }

    @Test
    void caffeineRoundTripServesWhatItStored() throws Exception {
        DashboardCache cache = cache("caffeine", 45);
        UUID user = UUID.randomUUID();
        DashboardResponse built = sample();

        cache.put(user, built);
        Optional<DashboardResponse> got = cache.get(user);

        assertThat(got).isPresent();
        // Records equal is too strict for the schemaless maps inside (JSON integers
        // read back as Integer, not Long) -- what must match is the wire output.
        assertThat(mapper.writeValueAsString(got.get()))
                .isEqualTo(mapper.writeValueAsString(built));
        // One user's entry is not another's:
        assertThat(cache.get(UUID.randomUUID())).isEmpty();
    }

    @Test
    void caffeineEntriesExpire() throws Exception {
        DashboardCache cache = cache("caffeine", 1);
        UUID user = UUID.randomUUID();
        cache.put(user, sample());

        Thread.sleep(1100);

        assertThat(cache.get(user)).isEmpty();
    }

    @Test
    void aPoisonedEntryIsEvictedRatherThanPinned() {
        UUID user = UUID.randomUUID();
        when(ops.get("careeros:v1:dashboard:" + user)).thenReturn("this is not json");
        DashboardCache cache = cache("redis", 45);

        assertThat(cache.get(user)).isEmpty();
        verify(redis).delete("careeros:v1:dashboard:" + user);
    }

    @Test
    void aRedisOutageIsAMissNotAnException() {
        UUID user = UUID.randomUUID();
        when(ops.get(anyString())).thenThrow(new IllegalStateException("connection refused"));
        org.mockito.Mockito.doThrow(new IllegalStateException("connection refused"))
                .when(ops).set(anyString(), anyString(), any(Duration.class));
        DashboardCache cache = cache("redis", 45);

        assertThat(cache.get(user)).isEmpty();
        assertThatCode(() -> cache.put(user, sample())).doesNotThrowAnyException();
    }

    @Test
    void hitsAndMissesAreCountedSeparately() {
        DashboardCache cache = cache("caffeine", 45);
        UUID user = UUID.randomUUID();
        cache.put(user, sample());
        cache.get(user);          // hit
        cache.get(UUID.randomUUID()); // miss

        assertThat(registry.get(DashboardCache.DECISIONS)
                .tag("backend", "caffeine").tag("outcome", "hit").counter().count()).isEqualTo(1.0);
        assertThat(registry.get(DashboardCache.DECISIONS)
                .tag("backend", "caffeine").tag("outcome", "miss").counter().count()).isEqualTo(1.0);
    }
}
