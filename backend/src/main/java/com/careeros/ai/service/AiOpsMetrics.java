package com.careeros.ai.service;

import com.careeros.ai.AiServiceClient;
import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicReference;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * The ai-service's own work-queue and cache readings, as the backend's Prometheus scrape sees
 * them (Epic 150).
 *
 * <p>The engine already computes two honest, read-only verdicts -- {@code GET
 * /internal/ops/workqueue} and {@code GET /internal/ops/cache}. They are the clean single source
 * an operator would read, but nothing scraped them: both carried a {@code no backend caller}
 * marker in docs/API.md because the product had no consumer. This collector is that consumer.
 * It asks the engine on a fixed delay and publishes the <em>raw numeric readings</em> those
 * verdicts already carry to the shared Micrometer registry, which is what {@code
 * /actuator/prometheus} exports. It adds no public route and lowers no authorization boundary:
 * the engine endpoints stay behind the shared internal token, and only aggregate numbers --
 * never the verdict sentence, the alert prose, or any per-key diagnostic -- leave this process.
 *
 * <p>Only measured numbers cross, deliberately. The verdict is a human summary computed from
 * these same numbers inside the engine; encoding that word as an integer here would invent a
 * severity ordering the engine never claimed (is "stalled" worse than "backlogged"?) and give a
 * dashboard a colour scale that implies a total order that does not exist. The numbers, the
 * engine's own {@code ok} flag, and {@code scrape_ok} below are enough to chart the queue and to
 * tell a dead engine from an empty one. The verdict text stays readable on the control-plane
 * endpoint for anyone who wants the engine's own judgement.
 *
 * <p><b>Fail-open, and honest about it.</b> A refresh that cannot reach one endpoint keeps that
 * half's last good readings and flips {@code scrape_ok} to 0; it never publishes a zero for "the
 * queue is empty", because a silent engine and an empty queue are different facts and a dashboard
 * that conflates them would report a dead worker as healthy. The two reads are independent, so a
 * cache endpoint that is momentarily unreachable does not blank the queue's numbers. Reads run on
 * the scheduler's thread and never throw into it.
 *
 * <p>Every meter this class registers is named in the roster gate
 * {@code test_the_alarms_name_metrics_that_ship_and_a_page_that_says_what_to_do.py} and in
 * docs/DEPLOYMENT.md. None is alarmed yet: the queue verdict is a new signal with no measured
 * good/bad baseline, and a threshold invented without one would page on a busy minute. They are
 * excused by name for dashboards until such a baseline exists -- the same decision already made
 * for {@code careeros_ratelimit_decisions_total}.
 */
@Component
public class AiOpsMetrics {

    /** Micrometer names; the Prometheus exporter renders dots as underscores. */
    static final String WORKQUEUE_DLQ = "careeros.ai.ops.workqueue.dlq.len";
    static final String WORKQUEUE_DELAYED = "careeros.ai.ops.workqueue.delayed.len";
    static final String WORKQUEUE_PENDING = "careeros.ai.ops.workqueue.pending";
    static final String WORKQUEUE_OK = "careeros.ai.ops.workqueue.ok";
    static final String CACHE_HIT_RATE = "careeros.ai.ops.cache.hit.rate";
    static final String CACHE_ERRORS = "careeros.ai.ops.cache.errors";
    static final String SCRAPE_OK = "careeros.ai.ops.scrape.ok";

    /**
     * The engine endpoints require a non-empty {@code X-User-Id} by the shared internal contract,
     * but both verdicts are fleet-wide and never scope by user. The nil UUID is an explicit,
     * non-personal value: it cannot collide with a real account and says in the wire what it is.
     */
    static final UUID SYSTEM_USER_ID = new UUID(0L, 0L);

    private static final Logger log = LoggerFactory.getLogger(AiOpsMetrics.class);

    private final AiServiceClient ai;
    /** One exchange's worth of readings, replaced atomically so a scrape is never half-updated. */
    private final AtomicReference<Reading> reading = new AtomicReference<>(Reading.empty());

    public AiOpsMetrics(AiServiceClient ai, MeterRegistry registry) {
        this.ai = ai;
        gauge(registry, WORKQUEUE_DLQ, "Jobs on the embed dead-letter stream", r -> r.workqueueDlq);
        gauge(registry, WORKQUEUE_DELAYED, "Embed jobs waiting out a retry backoff window", r -> r.workqueueDelayed);
        gauge(registry, WORKQUEUE_PENDING, "Unacknowledged embed-job entries in the consumer group", r -> r.workqueuePending);
        gauge(registry, WORKQUEUE_OK, "Whether the engine's own work-queue readings all succeeded", r -> r.workqueueOk);
        gauge(registry, CACHE_HIT_RATE, "RAG cache hit rate over the engine's own window", r -> r.cacheHitRate);
        gauge(registry, CACHE_ERRORS, "RAG cache errors counted by the engine", r -> r.cacheErrors);
        gauge(registry, SCRAPE_OK, "Whether the last refresh reached both engine verdict endpoints", r -> r.scrapeOk);
        refresh();
    }

    private void gauge(MeterRegistry registry, String name, String description,
                       java.util.function.ToDoubleFunction<Reading> value) {
        Gauge.builder(name, reading, ref -> value.applyAsDouble(ref.get()))
                .description(description)
                .register(registry);
    }

    /** Reads both engine verdicts. Runs on the scheduler's thread, never throws into it. */
    @Scheduled(fixedDelayString = "${careeros.ai.ops.metrics-refresh-ms:60000}")
    public void refresh() {
        Map<String, Object> queue;
        Map<String, Object> cache;
        try {
            queue = ai.workqueueVerdict(SYSTEM_USER_ID);
        } catch (RuntimeException e) {
            log.warn("work-queue verdict scrape failed; keeping the last reading", e);
            queue = null;
        }
        try {
            cache = ai.cacheVerdict(SYSTEM_USER_ID);
        } catch (RuntimeException e) {
            log.warn("cache verdict scrape failed; keeping the last reading", e);
            cache = null;
        }
        reading.set(project(queue, cache, reading.get()));
    }

    /**
     * Pure projection of the two engine answers into gauge values. An absent or empty answer is a
     * failed read, not a healthy zero: it keeps the last good numbers for that half and marks
     * {@code scrape_ok} as 0. The two answers are projected independently so one failing endpoint
     * cannot blank the other's numbers. This is a pure function of the inputs for easy offline
     * testing; it reads no clock, no Redis and no HTTP.
     */
    static Reading project(Map<String, Object> queue, Map<String, Object> cache, Reading previous) {
        boolean queueOk = queue != null && !queue.isEmpty();
        boolean cacheOk = cache != null && !cache.isEmpty();
        return new Reading(
                queueOk ? num(nested(queue, "queue", "dlq_len")) : previous.workqueueDlq,
                queueOk ? num(nested(queue, "queue", "delayed_len")) : previous.workqueueDelayed,
                queueOk ? num(nested(queue, "queue", "pending")) : previous.workqueuePending,
                queueOk ? flag(nested(queue, "queue", "ok")) : previous.workqueueOk,
                cacheOk ? num(nested(cache, "cache", "hit_rate")) : previous.cacheHitRate,
                cacheOk ? num(nested(cache, "cache", "errors")) : previous.cacheErrors,
                queueOk && cacheOk ? 1.0 : 0.0);
    }

    @SuppressWarnings("unchecked")
    private static Object nested(Map<String, Object> obj, String section, String key) {
        Object part = obj.get(section);
        return part instanceof Map<?, ?> m ? m.get(key) : null;
    }

    /** A boolean field becomes 1/0; a missing one is 0 for that field only. */
    private static double flag(Object value) {
        return Boolean.TRUE.equals(value) ? 1.0 : 0.0;
    }

    /** A missing or non-numeric field is 0 for that field only, never a failed whole refresh. */
    private static double num(Object value) {
        if (value instanceof Number n) {
            return n.doubleValue();
        }
        if (value instanceof String s) {
            try {
                return Double.parseDouble(s);
            } catch (NumberFormatException ignored) {
                return 0.0;
            }
        }
        return 0.0;
    }

    /** One coherent set of gauge values, swapped into {@link #reading} as a unit. */
    record Reading(double workqueueDlq, double workqueueDelayed, double workqueuePending,
                   double workqueueOk, double cacheHitRate, double cacheErrors, double scrapeOk) {
        static Reading empty() {
            return new Reading(0, 0, 0, 0, 0, 0, 0);
        }
    }
}
