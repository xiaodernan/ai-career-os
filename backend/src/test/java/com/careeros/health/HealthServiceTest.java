package com.careeros.health;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doReturn;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.ai.AiServiceClient;
import com.careeros.storage.StorageService;
import java.sql.Connection;
import java.time.Duration;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import javax.sql.DataSource;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.data.redis.core.RedisCallback;
import org.springframework.data.redis.core.RedisTemplate;

/**
 * The health line's four questions (roadmap 39.1).
 *
 * <p>Until this item the line asked the database and Redis and stayed silent about the object
 * store and the ai-service -- the two halves whose failure leaves a deployment that answers
 * every page and cannot upload a file or run a single feature. These tests pin the arithmetic:
 * {@code status} is {@code ok} only when all four answer, an absent store is reported rather
 * than skipped, a probe that throws is a false rather than an exception, and a probe that never
 * answers is cut off by the report's own budget instead of hanging the caller.
 *
 * <p>What mocks cannot state is that the two real probes speak the right protocols; that is
 * the HTTP bridge's own test over a socket and {@code HealthIT} against the real database,
 * Redis and in-memory store.
 */
class HealthServiceTest {

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
    }

    private HealthService service() {
        return new HealthService(dataSource, redis, Optional.of(storage), ai);
    }

    @Test
    void allFourAnsweringReportsOk() {
        Map<String, Object> report = service().report();

        assertThat(report.keySet()).containsExactly("status", "db", "redis", "storage", "ai");
        assertThat(report)
                .containsEntry("status", "ok")
                .containsEntry("db", true)
                .containsEntry("redis", true)
                .containsEntry("storage", true)
                .containsEntry("ai", true);
        verify(storage).available();
        verify(ai).healthy();
    }

    @Test
    void aStoreThatSaysNoDegradesTheLine() {
        when(storage.available()).thenReturn(false);

        assertThat(service().report())
                .containsEntry("status", "degraded")
                .containsEntry("storage", false)
                .containsEntry("db", true);
    }

    @Test
    void anAiHalfThatIsGoneDegradesTheLine() {
        when(ai.healthy()).thenReturn(false);

        assertThat(service().report())
                .containsEntry("status", "degraded")
                .containsEntry("ai", false);
    }

    @Test
    void anAiProbeThatThrowsIsAFalseRatherThanAnException() {
        when(ai.healthy()).thenThrow(new IllegalStateException("socket closed"));

        assertThat(service().report())
                .containsEntry("ai", false)
                .containsEntry("status", "degraded");
    }

    @Test
    void anAbsentStoreIsReportedRatherThanSkipped() {
        // app.storage.enabled=false is a deployment that never configured a bucket.
        // Its uploads cannot land, so the line must not claim a green half.
        HealthService service = new HealthService(dataSource, redis, Optional.empty(), ai);

        assertThat(service.report())
                .containsEntry("storage", false)
                .containsEntry("status", "degraded");
    }

    @Test
    void aDatabaseThatSaysNoDegradesTheLine() throws Exception {
        when(connection.isValid(2)).thenReturn(false);

        assertThat(service().report())
                .containsEntry("db", false)
                .containsEntry("status", "degraded");
    }

    @Test
    void aRedisThatThrowsDegradesTheLine() {
        doThrow(new IllegalStateException("connection refused"))
                .when(redis).execute(any(RedisCallback.class), eq(true));

        assertThat(service().report())
                .containsEntry("redis", false)
                .containsEntry("status", "degraded");
    }

    @Test
    void aProbeThatNeverAnswersIsBoundedAndReportedFalse() {
        CountDownLatch release = new CountDownLatch(1);
        when(storage.available()).thenAnswer(invocation -> {
            release.await(5, TimeUnit.SECONDS);
            return true;
        });
        HealthService service = new HealthService(dataSource, redis, Optional.of(storage), ai,
                Duration.ofMillis(100));

        long started = System.nanoTime();
        Map<String, Object> report;
        try {
            report = service.report();
        } finally {
            release.countDown();
        }
        long elapsedMs = TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - started);

        assertThat(report)
                .containsEntry("storage", false)
                .containsEntry("status", "degraded")
                .containsEntry("db", true)
                .containsEntry("redis", true)
                .containsEntry("ai", true);
        assertThat(elapsedMs).isLessThan(2000);
    }
}
