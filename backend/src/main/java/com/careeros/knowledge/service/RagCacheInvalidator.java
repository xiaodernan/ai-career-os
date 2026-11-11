package com.careeros.knowledge.service;

import com.careeros.ai.AiServiceClient;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;

/**
 * Retires the RAG cache's remembered answers once a delete that produced them is durable
 * (Finding B, Epic 147).
 *
 * <p>The delete path marks documents {@code status='retired'} inside a database
 * transaction. The ai-service's retrieval cache is a different process with a different
 * store, and it has no idea a row went away: a retrieval cached a moment before the
 * delete keeps quoting text the user just removed until its TTL. The reader's epoch is
 * the fix — bumping it makes every key under that user unreadable at once — but *when*
 * the bump happens is the whole bug.
 *
 * <p>Bumping inside the transaction is wrong. Until it commits, another replica reading
 * the same shared store still sees {@code status='ready'} on the not-yet-retired rows;
 * a bump at that instant just makes the reader re-fetch the *old, still-quotable* rows
 * under a fresh generation. The invalidation therefore runs in {@code afterCommit()},
 * mirroring {@link StoredObjectReclaimer}: the rows are durable and retired before any
 * reader is told to look again. A rollback never bumps. A call made with no active
 * transaction (e.g. a maintenance path) runs inline.
 *
 * <p>Invalidation is the last step of a delete that already succeeded, so an ai-service
 * that refuses is counted and logged — never turned into an error about a thing the
 * reader no longer has. The stale entry, if the bump did not land, still expires on its
 * own TTL; the delete itself stands. That is the honest failure boundary.
 */
@Service
public class RagCacheInvalidator {

    static final String INVALIDATED = "careeros.rag.cache_invalidations";
    private static final String DESCRIPTION =
            "RAG cache epoch bumps requested after a durable delete, by outcome";

    private static final Logger log = LoggerFactory.getLogger(RagCacheInvalidator.class);

    private final AiServiceClient ai;
    private final MeterRegistry registry;
    private final java.util.Map<String, Counter> counters = new java.util.concurrent.ConcurrentHashMap<>();

    public RagCacheInvalidator(AiServiceClient ai, MeterRegistry registry) {
        this.ai = ai;
        this.registry = registry;
    }

    /**
     * Retire this user's cached retrievals after the caller's transaction commits.
     * A null/blank user is a no-op — there is no generation to bump without an owner.
     */
    public void invalidateAfterCommit(UUID userId) {
        if (userId == null) {
            return;
        }
        if (!TransactionSynchronizationManager.isSynchronizationActive()) {
            bump(userId);
            return;
        }
        TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
            @Override
            public void afterCommit() {
                bump(userId);
            }
        });
    }

    /** One bump, one outcome — and an ai-service that refuses cannot undo the rows. */
    private void bump(UUID userId) {
        try {
            ai.invalidateCache(userId);
            record("requested");
        } catch (RuntimeException e) {
            record("failed");
            log.warn("RAG cache invalidation failed for user {}: {}", userId, e.getMessage());
        }
    }

    private void record(String outcome) {
        counters.computeIfAbsent(outcome, name -> Counter.builder(INVALIDATED)
                        .tag("outcome", name)
                        .description(DESCRIPTION)
                        .register(registry))
                .increment();
    }
}
