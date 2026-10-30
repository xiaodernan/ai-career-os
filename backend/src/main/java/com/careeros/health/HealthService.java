package com.careeros.health;

import com.careeros.ai.AiServiceClient;
import com.careeros.storage.StorageService;
import java.sql.Connection;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.FutureTask;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.function.BooleanSupplier;
import javax.sql.DataSource;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

/**
 * What this deployment can reach, asked from four directions at once.
 *
 * <p>Until 39.1 the health line asked the database and Redis and stayed silent about the
 * two halves that fail just as quietly: an object store that stopped answering and an
 * ai-service that is not running both leave a deployment that looks healthy and cannot
 * upload a resume or answer a single feature. Each dependency is now probed, all four
 * probes run together, and the report waits no longer than {@link #DEFAULT_PROBE_TIMEOUT}
 * in total -- a hung dependency is reported as not answering rather than hanging the
 * caller. The report is the body, the status code is not: the route always answers 200 so
 * a monitor can read which one is down instead of guessing from a refusal.
 */
@Service
public class HealthService {

    private static final Logger log = LoggerFactory.getLogger(HealthService.class);

    /** The whole report's budget, not each probe's: the four run concurrently. */
    static final Duration DEFAULT_PROBE_TIMEOUT = Duration.ofSeconds(2);

    private final DataSource dataSource;
    private final RedisTemplate<String, ?> redisTemplate;
    private final Optional<StorageService> storage;
    private final AiServiceClient aiService;
    private final Duration probeTimeout;

    @Autowired
    public HealthService(DataSource dataSource, RedisTemplate<String, ?> redisTemplate,
                         Optional<StorageService> storage, AiServiceClient aiService) {
        this(dataSource, redisTemplate, storage, aiService, DEFAULT_PROBE_TIMEOUT);
    }

    /** The test seam: a shorter bound than the shipped one, for a probe that never answers. */
    HealthService(DataSource dataSource, RedisTemplate<String, ?> redisTemplate,
                  Optional<StorageService> storage, AiServiceClient aiService,
                  Duration probeTimeout) {
        this.dataSource = dataSource;
        this.redisTemplate = redisTemplate;
        this.storage = storage;
        this.aiService = aiService;
        this.probeTimeout = probeTimeout;
    }

    /**
     * Four booleans and one verdict, in the order a reader asks them: the store every page
     * needs, the cache every login touches, the bucket every file lands in, the engine every
     * feature calls. {@code status} is {@code ok} only when all four answered; otherwise
     * {@code degraded}, because a deployment that cannot see one of its halves is not whole.
     */
    public Map<String, Object> report() {
        FutureTask<Boolean> db = startProbe("db", this::dbUp);
        FutureTask<Boolean> redis = startProbe("redis", this::redisUp);
        FutureTask<Boolean> store = startProbe("storage", this::storageUp);
        FutureTask<Boolean> ai = startProbe("ai", this::aiUp);

        long deadline = System.nanoTime() + probeTimeout.toNanos();
        boolean dbUp = await(db, deadline);
        boolean redisUp = await(redis, deadline);
        boolean storageUp = await(store, deadline);
        boolean aiUp = await(ai, deadline);

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("status", dbUp && redisUp && storageUp && aiUp ? "ok" : "degraded");
        body.put("db", dbUp);
        body.put("redis", redisUp);
        body.put("storage", storageUp);
        body.put("ai", aiUp);
        return body;
    }

    private static FutureTask<Boolean> startProbe(String name, BooleanSupplier probe) {
        FutureTask<Boolean> task = new FutureTask<>(probe::getAsBoolean);
        Thread.ofVirtual().name("health-" + name).start(task);
        return task;
    }

    /**
     * One probe's answer, or false if it did not answer inside what is left of the budget.
     * A timeout cancels the probe so a thread is not left waiting on a dependency that is
     * gone; an interrupt stops the wait and is restored, because the caller's own stop is
     * not this report's to swallow.
     */
    private static boolean await(FutureTask<Boolean> task, long deadlineNanos) {
        long remaining = deadlineNanos - System.nanoTime();
        try {
            return task.get(Math.max(remaining, 0), TimeUnit.NANOSECONDS);
        } catch (TimeoutException e) {
            task.cancel(true);
            return false;
        } catch (ExecutionException e) {
            log.warn("Health probe failed: {}", e.getCause() == null ? e.toString() : e.getCause().toString());
            return false;
        } catch (InterruptedException e) {
            task.cancel(true);
            Thread.currentThread().interrupt();
            return false;
        }
    }

    private boolean dbUp() {
        try (Connection connection = dataSource.getConnection()) {
            return connection.isValid(2);
        } catch (Exception e) {
            return false;
        }
    }

    private boolean redisUp() {
        try {
            redisTemplate.execute(connection -> connection.ping(), true);
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    /**
     * An absent bean is a deployment that did not configure an object store, which is a
     * "no" for anyone who tries to upload: reported, not skipped, so the line never claims
     * four green halves when one was never there.
     */
    private boolean storageUp() {
        return storage.map(StorageService::available).orElse(false);
    }

    private boolean aiUp() {
        try {
            return aiService.healthy();
        } catch (Exception e) {
            return false;
        }
    }
}
