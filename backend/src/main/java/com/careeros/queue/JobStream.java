package com.careeros.queue;

import java.time.Duration;
import java.util.List;
import java.util.Map;

/**
 * The narrow transport the job queue needs from Redis Streams (Epic 162).
 *
 * <p>Seven commands, no more: the point of naming them in an interface is that the queue's
 * policy -- who may run a job, when a job is finished, when it is poison -- is testable
 * without a socket, and the real implementation is the only file that knows a Redis
 * command's spelling. {@code JobQueueTest}/{@code JobWorkerTest} drive a fake that keeps the
 * same consumer-group bookkeeping; {@code JobQueueIT} drives this port's Redis implementation
 * against a real server, because a fake cannot contradict XCLAIM's idle re-check.
 *
 * <p>Delivery semantics are at-least-once. A read hands an entry to one consumer and puts it
 * in that group's pending-entries list (PEL); only {@link #ack} takes it out. A consumer that
 * dies mid-job therefore leaves work behind rather than losing it, and {@link #claim} is how
 * a sibling picks it up. Every handler must be idempotent: the queue promises a job runs, not
 * that it runs once.
 */
public interface JobStream {

    /** Creates the group (and the stream) if absent; a group that already exists is not an error. */
    void ensureGroup();

    /** Appends one job, trimming the stream to its bounded length. Returns the entry id. */
    String add(Map<String, String> fields);

    /** Appends one job to the dead-letter stream, so a poison job stops burning a worker. */
    String addDead(Map<String, String> fields);

    /** Up to {@code count} entries nobody has been handed yet, for this consumer. */
    List<Entry> read(String consumer, int count);

    /** Up to {@code count} handed-but-unacknowledged entries, with their delivery counts. */
    List<Pending> pending(int count);

    /**
     * Takes ownership of the named entries whose last delivery is older than {@code minIdle}.
     * Redis re-checks the idle time, so an entry a live consumer is still working on is not
     * returned even when it is named here.
     */
    List<Entry> claim(String consumer, Duration minIdle, List<String> ids);

    /** Removes an entry from the group's PEL: the job is finished, or it has been dead-lettered. */
    void ack(String id);

    /** One entry as the handler sees it. */
    record Entry(String id, Map<String, String> fields) {
    }

    /**
     * One PEL row. {@code deliveries} counts deliveries <em>so far</em>: claiming the entry
     * makes it one more, which is the arithmetic {@link JobWorker} uses to bound attempts.
     */
    record Pending(String id, String consumer, Duration idle, long deliveries) {
    }
}