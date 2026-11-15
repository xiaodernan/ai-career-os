package com.careeros.admin;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.github.benmanes.caffeine.cache.Cache;
import com.github.benmanes.caffeine.cache.Caffeine;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import java.time.Duration;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

/**
 * The operator's read-through cache (Epic 253).
 *
 * <p>{@code GET /api/v1/admin/stats} and {@code /trends} are counted straight off the
 * tables — 20 and 5 aggregations respectively — and both read identically on every call:
 * the install's size does not move meaningfully inside a minute, and the page's own
 * re-render already polls slower than that. The cache is deliberately simple, mirroring
 * the dashboard's (Epic 125): a short TTL and nothing else. A±10% uniform TTL spread on
 * the Redis branch so N replicas never refill the same key at the same instant; Caffeine
 * stays fixed because a process-local expiry cannot dogpile a fleet.
 *
 * <p>Three backends, selected by {@code careeros.admin.cache} (default {@code off}):
 * <ul>
 *   <li>{@code off} — passthrough, the pre-cache behaviour, byte for byte;</li>
 *   <li>{@code caffeine} — process-local, bounded (64 entries), no new infrastructure;</li>
 *   <li>{@code redis} — shared across replicas, same connection the sliding-window limiter uses.</li>
 * </ul>
 *
 * <p>Fail-open on every branch, the dashboard's own posture: a Redis outage is a cache
 * miss plus a warn line, never a failed ledger. A payload that fails to round-trip is
 * treated as a miss and evicted, so a poisoned entry cannot pin itself in place. A
 * 60-second-stale install tally is the entire cost of being wrong here — the numbers
 * move slower than any reader refresh.
 */
@Component
public class AdminCache {

    private static final Logger log = LoggerFactory.getLogger(AdminCache.class);

    /** Cache key prefix; bump when the payload shape changes incompatibly. */
    static final String KEY_PREFIX = "careeros:v1:admin:";

    /** The Prometheus counters; `_total` is the exporter's suffix. */
    static final String DECISIONS = "careeros.admin.cache";

    private final String mode;
    private final Duration ttl;
    private final StringRedisTemplate redis;
    private final Cache<String, String> local;
    private final ObjectMapper mapper;
    private final MeterRegistry registry;
    private final Map<String, Counter> counters = new ConcurrentHashMap<>();

    public AdminCache(StringRedisTemplate redis,
                      MeterRegistry registry,
                      ObjectMapper mapper,
                      @Value("${careeros.admin.cache:off}") String mode,
                      @Value("${careeros.admin.cache-ttl-seconds:30}") long ttlSeconds) {
        String normalized = mode == null ? "off" : mode.trim().toLowerCase(Locale.ROOT);
        this.mode = switch (normalized) {
            case "", "off", "false", "0", "no" -> "off";
            case "caffeine", "redis" -> normalized;
            default -> {
                log.warn("careeros.admin.cache={} is not a known backend (off|caffeine|redis); running as off",
                        mode);
                yield "off";
            }
        };
        this.ttl = Duration.ofSeconds(Math.max(1, ttlSeconds));
        this.redis = redis;
        this.registry = registry;
        this.mapper = mapper;
        this.local = "caffeine".equals(this.mode)
                ? Caffeine.newBuilder().maximumSize(64).expireAfterWrite(this.ttl).build()
                : null;
    }

    /** The configured backend's name, for the tests and the operator. */
    public String mode() {
        return mode;
    }

    /** The cached payload for this key, or empty on off/miss/unreadable (evicted). */
    public Optional<Map<String, Object>> get(String subKey) {
        if ("off".equals(mode)) {
            record("off");
            return Optional.empty();
        }
        String key = KEY_PREFIX + subKey;
        String json = read(key);
        if (json == null) {
            record("miss");
            return Optional.empty();
        }
        try {
            @SuppressWarnings("unchecked")
            Map<String, Object> value = mapper.readValue(json, Map.class);
            record("hit");
            @SuppressWarnings("unchecked")
            Map<String, Object> normalized = (Map<String, Object>) deepNormalize(value);
            return Optional.of(normalized);
        } catch (Exception e) {
            log.warn("admin cache entry for {} is unreadable ({}); evicting it", key, e.toString());
            evict(key);
            record("miss");
            return Optional.empty();
        }
    }

    /** Store the payload for this key. Failures are swallowed: a cache is not the read path. */
    public void put(String subKey, Map<String, Object> value) {
        if ("off".equals(mode)) {
            return;
        }
        String key = KEY_PREFIX + subKey;
        try {
            String json = mapper.writeValueAsString(value);
            write(key, json);
        } catch (Exception e) {
            log.warn("admin cache write for {} failed: {}", key, e.toString());
        }
    }

    /**
     * Jackson reads a JSON `5` as an Integer; a computed payload carries a Long. Walk the
     * tree and widen every narrow integer to a Long so a cache hit is byte-consistent
     * with a computed answer — the ledger must not answer one shape on a miss and another
     * on a hit.
     */
    static Object deepNormalize(Object node) {
        if (node instanceof Map<?, ?> map) {
            Map<String, Object> out = new java.util.LinkedHashMap<>();
            for (Map.Entry<?, ?> entry : map.entrySet()) {
                out.put(String.valueOf(entry.getKey()), deepNormalize(entry.getValue()));
            }
            return out;
        }
        if (node instanceof List<?> list) {
            java.util.List<Object> out = new java.util.ArrayList<>(list.size());
            for (Object item : list) {
                out.add(deepNormalize(item));
            }
            return out;
        }
        if (node instanceof Integer || node instanceof Short || node instanceof Byte) {
            return ((Number) node).longValue();
        }
        return node;
    }

    private String read(String key) {
        try {
            if (local != null) {
                return local.getIfPresent(key);
            }
            return redis.opsForValue().get(key);
        } catch (RuntimeException e) {
            log.warn("admin cache read failed for {}: {}", key, e.toString());
            return null;
        }
    }

    private void write(String key, String json) {
        try {
            if (local != null) {
                local.put(key, json);
                return;
            }
            redis.opsForValue().set(key, json, Duration.ofSeconds(
                    jitterSeconds(ttl.getSeconds(), java.util.concurrent.ThreadLocalRandom.current())));
        } catch (RuntimeException e) {
            log.warn("admin cache write failed for {}: {}", key, e.toString());
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
            log.warn("admin cache eviction failed for {}: {}", key, e.toString());
        }
    }

    private void record(String outcome) {
        counters.computeIfAbsent(mode + "/" + outcome, unused -> Counter.builder(DECISIONS)
                        .tag("backend", mode)
                        .tag("outcome", outcome)
                        .description("Admin ledger cache decisions")
                        .register(registry))
                .increment();
    }

    /**
     * A ±10% uniform spread around the base TTL (floor 1s), same reasoning as the dashboard
     * cache: N replicas refilling one key on one expiry is one dogpile per window.
     * Package-private so the suite can pin the band with a seeded source.
     */
    static long jitterSeconds(long baseSeconds, java.util.Random random) {
        long base = Math.max(1, baseSeconds);
        long spread = Math.max(1, Math.round(base * 0.1));
        long jittered = base - spread + (long) (random.nextDouble() * (2L * spread + 1));
        return Math.max(1, jittered);
    }
}
