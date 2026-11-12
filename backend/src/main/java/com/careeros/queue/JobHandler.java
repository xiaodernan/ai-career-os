package com.careeros.queue;

import java.util.Map;

/**
 * One kind of background job, and the code that runs it.
 *
 * <p>A handler must be idempotent. The queue is at-least-once: a replica that dies after the
 * work but before the ack leaves the entry pending, and a sibling will run it again. A
 * handler that throws is not a lost job -- the entry stays in the PEL and is retried until
 * the delivery bound sends it to the dead-letter stream.
 */
public interface JobHandler {

    /** The wire name a producer enqueues under; unique across the registered handlers. */
    String kind();

    /** Runs one job. The payload is the producer's fields, without the routing {@code kind}. */
    void handle(Map<String, String> payload);
}