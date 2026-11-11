package com.careeros.report.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.github.benmanes.caffeine.cache.Cache;
import com.github.benmanes.caffeine.cache.Caffeine;
import com.careeros.report.dto.DashboardDtos.DashboardResponse;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import java.time.Duration;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

/**
 * The dashboard's read-through cache (Epic 125).
 *
 * <p>GET /api/v1/reports/dashboard is the one endpoint every app open hits, and it was
 * rebuilt from the ground truth every time. It is read-mostly -- the writes that touch
 * it (an application moves, a reminder is answered, a letter lands) are exactly the same
 * writes that make it interesting -- so the cache below is deliberately simple: a
 * short TTL and nothing else. No write-path invalidation, no versioned keys, no
 * coherence protocol. A reader who just moved a card waits one TTL at most for the
 * strip to agree; the trade the service already makes for the rest of the loop.
 *
 * <p>Three backends, selected by {@code careeros.dashboard.cache} (default {@code off}):
 * <ul>
 *   <li>{@code off} -- passthrough, the pre-cache behaviour, byte for byte;</li>
 *   <li>{@code caffeine} -- process-local, bounded (256 entries), no new infrastructure;</li>
 *   <li>{@code redis} -- shared across replicas via {@link StringRedisTemplate}, same
 *       connection the sliding-window rate limiter already uses.</li>
 * </ul>
 *
 * <p>Spelling matters: YAML 1.1 parses a bare `off` as the boolean {@code false},
 * so a yml config arrives here as the string {@code false}. The constructor normalizes
 * the empty string, {@code off}, {@code false}, {@code 0} and {@code no} to off, and
 * anything it does not recognize fails closed to off with a warn -- a typo loses the
 * cache, not correctness. The yml in this repository spells the value quoted for the
 * same reason.
 *
 * <p>Fail-open on every branch, the limiter's own posture: a Redis outage is a cache
 * miss plus a warn log line, never a failed dashboard. A payload that fails to
 * round-trip (a future DTO field Jackson cannot name, a corrupted entry) is treated
 * as a miss and evicted, so a poisoned entry cannot pin itself in place.
 */
@Component
public class DashboardCache {

    private static final Logger log = LoggerFactory.getLogger(DashboardCache.class);

    /** Cache key prefix; bump the version when the payload shape changes incompatibly. */
    static final String KEY_PREFIX = "careeros:v1:dashboard:";

    /** The Prometheus counters; dots render as underscores and counters as `_total`. */
    static final String DECISIONS = "careeros.dashboard.cache";

    private final String mode;
    private final Duration ttl;
    private final StringRedisTemplate redis;
    private final Cache<String, String> local;
    private final ObjectMapper mapper;
    private final MeterRegistry registry;
    private final Map<String, Counter> counters = new ConcurrentHashMap<>();

    public DashboardCache(StringRedisTemplate redis,
                          MeterRegistry registry,
                          ObjectMapper mapper,
                          @Value("${careeros.dashboard.cache:off}") String mode,
                          @Value("${careeros.dashboard.cache-ttl-seconds:45}") long ttlSeconds) {
        // YAML 1.1 parses a bare `off` as the boolean false, so a yml spelling of the
        // intended value arrives here as the string "false" (an env var arrives intact,
        // which is why prod was correct and the dev yml was not). Unknown spellings fail
        // closed to off: a typo loses the cache, not correctness.
        String normalized = mode == null ? "off" : mode.trim().toLowerCase(Locale.ROOT);
        this.mode = switch (normalized) {
            case "", "off", "false", "0", "no" -> "off";
            case "caffeine", "redis" -> normalized;
            default -> {
                log.warn("careeros.dashboard.cache={} is not a known backend (off|caffeine|redis); running as off",
                        mode);
                yield "off";
            }
        };
        this.ttl = Duration.ofSeconds(Math.max(1, ttlSeconds));
        this.redis = redis;
        this.registry = registry;
        this.mapper = mapper;
        this.local = "caffeine".equals(this.mode)
                ? Caffeine.newBuilder().maximumSize(256).expireAfterWrite(this.ttl).build()
                : null;
    }

    /** The configured backend's name, for the tests and the operator. */
    public String mode() {
        return mode;
    }

    /**
     * The cached payload for this reader, or empty when the mode is off, the entry
     * is absent or expired, or the entry is unreadable (in which case it is evicted
     * so the next write replaces it rather than re-reading it forever).
     */
    public Optional<DashboardResponse> get(UUID userId) {
        if ("off".equals(mode)) {
            record("off");
            return Optional.empty();
        }
        String key = KEY_PREFIX + userId;
        String json = read(key);
        if (json == null) {
            record("miss");
            return Optional.empty();
        }
        try {
            record("hit");
            return Optional.of(mapper.readValue(json, DashboardResponse.class));
        } catch (Exception e) {
            log.warn("dashboard cache entry for {} is unreadable ({}); evicting it", userId, e.toString());
            evict(key);
            record("miss");
            return Optional.empty();
        }
    }

    /** Store the payload for this reader. Failures are swallowed: a cache is not the read path. */
    public void put(UUID userId, DashboardResponse response) {
        if ("off".equals(mode)) {
            return;
        }
        String key = KEY_PREFIX + userId;
        try {
            String json = mapper.writeValueAsString(response);
            write(key, json);
        } catch (Exception e) {
            log.warn("dashboard cache write for {} failed: {}", userId, e.toString());
        }
    }

    private String read(String key) {
        try {
            if (local != null) {
                return local.getIfPresent(key);
            }
            return redis.opsForValue().get(key);
        } catch (RuntimeException e) {
            log.warn("dashboard cache read failed for {}: {}", key, e.toString());
            return null;
        }
    }

    private void write(String key, String json) {
        try {
            if (local != null) {
                local.put(key, json);
                return;
            }
            redis.opsForValue().set(key, json, ttl);
        } catch (RuntimeException e) {
            log.warn("dashboard cache write failed for {}: {}", key, e.toString());
        }
    }

    private void evict(String key) {
        try {
            if (local != null) {
                local.invalidate(key);
                return;
            }
            redis.delete(key);
        } catch (RuntimeException e) {
            log.warn("dashboard cache eviction failed for {}: {}", key, e.toString());
        }
    }

    private void record(String outcome) {
        counters.computeIfAbsent(mode + "/" + outcome, unused -> Counter.builder(DECISIONS)
                        .tag("backend", mode)
                        .tag("outcome", outcome)
                        .description("Dashboard cache decisions")
                        .register(registry))
                .increment();
    }
}
