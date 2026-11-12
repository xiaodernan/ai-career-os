package com.careeros.queue;

import java.util.LinkedHashMap;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/**
 * The producer's door to the backend's job queue (Epic 162).
 *
 * <p>Opt-in, like every other distributed element in this repo: {@code careeros.queue.enabled}
 * defaults to false, and a disabled queue sends no Redis command and registers no series. The
 * caller keeps its own inline path, so turning the queue on is a durability upgrade and never
 * a new dependency -- {@link #enqueue} answers false when the queue is off <em>or</em> when
 * Redis refuses the write, and the caller does what it did before.
 *
 * <p>That is the whole failure boundary. A delete that already committed must not fail because
 * a queue is unreachable, and it must not silently lose its invalidation either: the caller
 * falls back to the inline call, which is exactly today's behaviour.
 *
 * <p>No timestamp field is written. A Redis stream id <em>is</em> a millisecond clock plus a
 * sequence number, so the entry's own id carries its age; a second copy of the same fact in
 * the payload would be one more thing to keep true.
 */
@Component
public class JobQueue {

    /** The routing field every entry carries; the worker reads it to pick a handler. */
    public static final String KIND_FIELD = "kind";

    private static final Logger log = LoggerFactory.getLogger(JobQueue.class);

    private final JobStream stream;
    private final QueueMetrics metrics;
    private final boolean enabled;

    public JobQueue(JobStream stream, QueueMetrics metrics,
                    @Value("${careeros.queue.enabled:false}") boolean enabled) {
        this.stream = stream;
        this.metrics = metrics;
        this.enabled = enabled;
    }

    /** Whether this process enqueues at all. The worker reads the same switch. */
    public boolean enabled() {
        return enabled;
    }

    /**
     * Hands one job to the fleet. True only when the entry is durable in the stream; false
     * means the caller must do the work itself, now, exactly as it did before the queue existed.
     */
    public boolean enqueue(String kind, Map<String, String> payload) {
        if (!enabled) {
            return false;
        }
        Map<String, String> fields = new LinkedHashMap<>(payload);
        fields.put(KIND_FIELD, kind);
        try {
            stream.add(fields);
            metrics.count(kind, "enqueued");
            return true;
        } catch (RuntimeException e) {
            metrics.count(kind, "dropped");
            log.warn("queue enqueue of {} failed ({}); the caller keeps its inline path", kind, e.toString());
            return false;
        }
    }
}