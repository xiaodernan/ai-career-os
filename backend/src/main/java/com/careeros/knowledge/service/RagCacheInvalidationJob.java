package com.careeros.knowledge.service;

import com.careeros.queue.JobHandler;
import java.util.Map;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

/**
 * The RAG cache invalidation as a fleet job (Epic 417).
 *
 * <p>An epoch bump is the cheapest possible idempotent job: the reader's generation is a
 * counter, so running the same invalidation twice retires the same cached answers twice and
 * the second run reads the same empty result. That is exactly the property the handler
 * contract demands, and it is why a job this small rides the queue at all — the work a
 * replica would do inline is work another replica can do just as correctly, later, after a
 * crash, with the entry still visible in the group's pending list until somebody acks it.
 *
 * <p>The payload is the owner and nothing else. No timestamp is copied in: the entry's stream
 * id already carries the millisecond it was enqueued, and the bump does not care when the
 * delete happened — only that no cached answer outlives the row that produced it.
 *
 * <p>A payload that does not name a user is acknowledged, not retried. The retry ladder exists
 * for a dependency that may answer next time; a malformed UUID answers the same way forever,
 * and an entry that burns five deliveries to discover that is a poisoned queue, not a retried
 * job. This can happen during a rolling deploy, where an older replica enqueues a field the
 * newer ones no longer read; the delete itself already committed, and the cached answer it
 * left behind still expires on its own TTL.
 */
@Component
public class RagCacheInvalidationJob implements JobHandler {

    /** The wire name the invalidator enqueues under. */
    public static final String KIND = "rag.cache.invalidate";

    /** The payload's only field: the owner whose cached retrievals are being retired. */
    public static final String USER_FIELD = "userId";

    private static final Logger log = LoggerFactory.getLogger(RagCacheInvalidationJob.class);

    private final RagCacheInvalidator invalidator;

    public RagCacheInvalidationJob(RagCacheInvalidator invalidator) {
        this.invalidator = invalidator;
    }

    @Override
    public String kind() {
        return KIND;
    }

    @Override
    public void handle(Map<String, String> payload) {
        UUID userId;
        try {
            userId = UUID.fromString(payload.get(USER_FIELD));
        } catch (IllegalArgumentException | NullPointerException e) {
            log.warn("queue entry named no readable user ({} field = {}); acknowledged instead of retried",
                    USER_FIELD, payload.get(USER_FIELD));
            return;
        }
        invalidator.bump(userId);
    }
}
