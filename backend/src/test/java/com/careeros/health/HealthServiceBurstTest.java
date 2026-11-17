package com.careeros.health;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doReturn;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.ai.AiServiceClient;
import com.careeros.storage.StorageService;
import java.sql.Connection;
import java.time.Duration;
import java.util.Map;
import java.util.Optional;
import javax.sql.DataSource;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.data.redis.core.RedisCallback;
import org.springframework.data.redis.core.RedisTemplate;

/**
 * The burst cache and the liveness line (Epic 314).
 *
 * <p>The readiness report used to be recomputed on every call; a 100-way dashboard
 * fan-out turned into 400 database connections and everyone waited. The report now
 * shares one computed answer for a two-second monotonic budget, and the liveness
 * line asks nothing at all. These tests pin both, plus the honesty of the cache:
 * it recomputes on a zero TTL, hands out a copy the caller cannot corrupt, and
 * never hides a degraded verdict.
 */
class HealthServiceBurstTest {

    private DataSource dataSource;
    private Connection connection;
    private RedisTemplate<String, Object> redis;
    private StorageService storage;
    private AiServiceClient ai;

    @BeforeEach
    void setUp() throws Exception {
        dataSource = mock(DataSource.class);
        connection = mock(Connection.class);
        when(dataSource.getConnection()).thenReturn(connection);
        when(connection.isValid(2)).thenReturn(true);

        redis = mock(RedisTemplate.class);
        doReturn("PONG").when(redis).execute(any(RedisCallback.class), eq(true));

        storage = mock(StorageService.class);
        when(storage.available()).thenReturn(true);

        ai = mock(AiServiceClient.class);
        when(ai.healthy()).thenReturn(true);
        when(ai.healthyNodes()).thenReturn(Map.of("http://ai-service:8000", true));
    }

    @Test
    void aBurstSharesOneComputedReportWithinTheTtl() {
        HealthService service = new HealthService(dataSource, redis, Optional.of(storage), ai,
                Duration.ofSeconds(2), Duration.ofSeconds(2));

        Map<String, Object> first = service.reportCached();
        Map<String, Object> second = service.reportCached();

        assertThat(first).isEqualTo(second);
        verify(storage, org.mockito.Mockito.times(1)).available();
    }

    @Test
    void aZeroTtlNeverCaches() {
        HealthService service = new HealthService(dataSource, redis, Optional.of(storage), ai,
                Duration.ofSeconds(2), Duration.ZERO);

        service.reportCached();
        service.reportCached();

        verify(storage, org.mockito.Mockito.times(2)).available();
    }

    @Test
    void theCachedReportIsACopyTheCallerCannotCorrupt() {
        HealthService service = new HealthService(dataSource, redis, Optional.of(storage), ai,
                Duration.ofSeconds(2), Duration.ofSeconds(2));

        service.reportCached().put("status", "corrupted");

        assertThat(service.reportCached().get("status")).isEqualTo("ok");
    }

    @Test
    void aDegradedReportIsCachedHonestlyNeverHidden() {
        when(storage.available()).thenReturn(false);
        HealthService service = new HealthService(dataSource, redis, Optional.of(storage), ai,
                Duration.ofSeconds(2), Duration.ofSeconds(2));

        assertThat(service.reportCached().get("status")).isEqualTo("degraded");
        assertThat(service.reportCached().get("status")).isEqualTo("degraded");
        verify(storage, org.mockito.Mockito.times(1)).available();
    }

    @Test
    void livenessAnswersOkAndAsksNothing() {
        HealthService service = new HealthService(dataSource, redis, Optional.of(storage), ai);

        Map<String, Object> live = service.liveness();

        assertThat(live.get("status")).isEqualTo("ok");
        assertThat(live.get("kind")).isEqualTo("liveness");
        assertThat(((Number) live.get("uptimeMs")).longValue()).isGreaterThanOrEqualTo(0);
        verify(storage, never()).available();
        verify(ai, never()).healthyNodes();
    }
}
