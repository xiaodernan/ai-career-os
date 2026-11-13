package com.careeros.queue;

import com.careeros.queue.JobStream.Entry;
import com.careeros.queue.JobStream.Pending;
import java.lang.management.ManagementFactory;
import java.time.Duration;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * The consumer half of the queue: one tick takes work, runs it, and acknowledges only what
 * finished.
 *
 * <p><b>Why a consumer group and not a list.</b> {@code BRPOP} on a list hands a job to whoever
 * asks, and a worker that dies after the pop has already taken the job out of the world. A
 * group's pending-entries list keeps the job visible until an explicit XACK, so a crashed
 * replica's work is <em>reclaimable</em> rather than lost. That is the property the backend's
 * {@code @Scheduled} walks never had: with three replicas they each ran the same sweep, and
 * with one replica a failure between "read" and "done" was silent.
 *
 * <p><b>The attempt arithmetic.</b> A fresh XREADGROUP is attempt 1. A reclaim is one more
 * delivery, so an entry whose PEL row already reports {@code maxDeliveries} deliveries has had
 * its last chance: it goes to the dead-letter stream and is acknowledged, which is what stops
 * a poison job from burning a worker on every tick forever. The bound is on deliveries, not on
 * wall-clock age, so a job that keeps failing fast is retired just as surely as one that hangs.
 *
 * <p><b>Idle, not absent.</b> Reclaim only names entries whose last delivery is older than
 * {@code claim-idle-ms}, and Redis re-checks that idle time inside XCLAIM -- a sibling that is
 * merely slow keeps its own work. The consumer name is this process's {@code pid@host}, unique
 * per replica and stable for its lifetime, which is what makes "whose job is this" decidable
 * after a crash.
 *
 * <p>A tick that cannot reach Redis logs and returns: the entries are still in the stream, and
 * the next tick is the retry. Nothing here turns a queue outage into a failed request.
 */
@Component
public class JobWorker {

    private static final Logger log = LoggerFactory.getLogger(JobWorker.class);

    private final JobStream stream;
    private final JobQueue queue;
    private final QueueMetrics metrics;
    private final Map<String, JobHandler> handlers;
    private final String consumer;
    private final int batch;
    private final long maxDeliveries;
    private final Duration claimIdle;
    private boolean groupReady;

    public JobWorker(JobStream stream, JobQueue queue, QueueMetrics metrics, List<JobHandler> handlers,
                     @Value("${careeros.queue.batch-size:20}") int batch,
                     @Value("${careeros.queue.max-deliveries:5}") long maxDeliveries,
                     @Value("${careeros.queue.claim-idle-ms:30000}") long claimIdleMs) {
        this.stream = stream;
        this.queue = queue;
        this.metrics = metrics;
        Map<String, JobHandler> byKind = new LinkedHashMap<>();
        for (JobHandler handler : handlers) {
            JobHandler previous = byKind.put(handler.kind(), handler);
            if (previous != null) {
                throw new IllegalStateException("two job handlers claim the kind " + handler.kind());
            }
        }
        this.handlers = Map.copyOf(byKind);
        this.consumer = ManagementFactory.getRuntimeMXBean().getName();
        this.batch = Math.max(1, batch);
        this.maxDeliveries = Math.max(1, maxDeliveries);
        this.claimIdle = Duration.ofMillis(Math.max(1, claimIdleMs));
    }

    /** This replica's name in the group, for the operator and the tests. */
    public String consumerName() {
        return consumer;
    }

    @Scheduled(fixedDelayString = "${careeros.queue.poll-ms:1000}")
    public void tick() {
        if (!queue.enabled()) {
            return;
        }
        try {
            if (!groupReady) {
                stream.ensureGroup();
                groupReady = true;
            }
            reclaim();
            drain();
        } catch (RuntimeException e) {
            // A group that vanishes mid-life (Redis flush, an operator's XGROUP DESTROY, or
            // a delete on the stream key) answers NOGROUP to every subsequent command. The
            // process-local groupReady flag would otherwise pin this replica permanently
            // broken for the process. The marker lives in the nested cause, not in the
            // top-level wrapper's toString(), so walk the cause chain.
            if (hasCause(e, "NOGROUP")) {
                groupReady = false;
            }
            log.warn("queue tick failed", e);
        }
    }

    /** Older work first: a job a sibling left behind is picked up before new work is taken. */
    private void reclaim() {
        List<Pending> pending = stream.pending(batch);
        Map<String, Long> deliveries = new HashMap<>();
        List<String> idle = new ArrayList<>();
        for (Pending row : pending) {
            if (row.idle().compareTo(claimIdle) < 0) {
                continue;
            }
            idle.add(row.id());
            deliveries.put(row.id(), row.deliveries());
        }
        if (idle.isEmpty()) {
            return;
        }
        for (Entry entry : stream.claim(consumer, claimIdle, idle)) {
            String kind = metricKind(entry);
            if (deliveries.getOrDefault(entry.id(), 0L) >= maxDeliveries) {
                deadLetter(entry, "max-deliveries");
                metrics.count(kind, "dead");
                continue;
            }
            metrics.count(kind, "reclaimed");
            run(entry);
        }
    }

    private void drain() {
        for (Entry entry : stream.read(consumer, batch)) {
            run(entry);
        }
    }

    private void run(Entry entry) {
        JobHandler handler = handlers.get(entry.fields().get(JobQueue.KIND_FIELD));
        if (handler == null) {
            // An entry no handler claims is poison by definition: retrying it cannot succeed.
            deadLetter(entry, "no-handler");
            metrics.count("unknown", "dead");
            log.warn("queue entry {} names no handler; dead-lettered", entry.id());
            return;
        }
        Map<String, String> payload = new LinkedHashMap<>(entry.fields());
        payload.remove(JobQueue.KIND_FIELD);
        try {
            handler.handle(payload);
        } catch (RuntimeException e) {
            metrics.count(handler.kind(), "failed");
            log.warn("job {} ({}) failed; leaving it pending for a retry: {}",
                    entry.id(), handler.kind(), e.toString());
            return;
        }
        stream.ack(entry.id());
        metrics.count(handler.kind(), "done");
    }

    /**
     * Records the job where an operator can read it, then acknowledges it. The order is the
     * point: a dead-letter write that fails leaves the entry pending, so a job is never dropped
     * because the place that records dropped jobs was unreachable.
     */
    private void deadLetter(Entry entry, String reason) {
        Map<String, String> fields = new LinkedHashMap<>(entry.fields());
        fields.put("reason", reason);
        fields.put("from", entry.id());
        stream.addDead(fields);
        stream.ack(entry.id());
    }

    /** The tag is the registered handler's name, so a bad payload cannot mint a new series. */
    private static boolean hasCause(Throwable e, String needle) {
        for (Throwable cause = e; cause != null; cause = cause.getCause()) {
            String message = cause.getMessage();
            if (message != null && message.contains(needle)) {
                return true;
            }
        }
        return false;
    }

    private String metricKind(Entry entry) {
        String wire = entry.fields().get(JobQueue.KIND_FIELD);
        return handlers.containsKey(wire) ? wire : "unknown";
    }
}