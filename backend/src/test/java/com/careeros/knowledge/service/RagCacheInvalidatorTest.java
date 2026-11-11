package com.careeros.knowledge.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;

import com.careeros.ai.AiServiceClient;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;

/**
 * Finding B (Epic 147): a delete retires its documents in a DB transaction, but the
 * ai-service's RAG cache is another process — it must be told to bump the reader's epoch
 * AFTER that transaction commits, or another replica re-fetches rows that are still
 * 'ready' under the freshly bumped generation. This is the after-commit discipline
 * {@link StoredObjectReclaimer} established for objects, applied to a cache generation.
 *
 * <p>Everything here is offline: a mock client stands in for the HTTP boundary and the
 * transaction synchronizations are driven by hand, exactly as the reclaimer's tests do.
 */
class RagCacheInvalidatorTest {

    private static final UUID USER = UUID.fromString("00000000-0000-0000-0000-0000000000aa");

    private AiServiceClient ai;
    private SimpleMeterRegistry registry;
    private RagCacheInvalidator invalidator;

    @BeforeEach
    void setUp() {
        ai = mock(AiServiceClient.class);
        registry = new SimpleMeterRegistry();
        invalidator = new RagCacheInvalidator(ai, registry);
    }

    @Test
    void withNoActiveTransactionTheBumpRunsInline() {
        invalidator.invalidateAfterCommit(USER);

        verify(ai).invalidateCache(USER);
        assertThat(count("requested")).isEqualTo(1.0);
    }

    @Test
    void aBumpInsideATransactionWaitsForThatTransactionToCommit() {
        TransactionSynchronizationManager.initSynchronization();
        try {
            invalidator.invalidateAfterCommit(USER);

            // The rows are not durable yet. Bumping now would let another replica
            // re-fetch the still-'ready' rows under a new generation — the exact bug.
            verify(ai, never()).invalidateCache(USER);
            assertThat(count("requested")).isZero();

            commit();

            verify(ai).invalidateCache(USER);
            assertThat(count("requested")).isEqualTo(1.0);
        } finally {
            TransactionSynchronizationManager.clearSynchronization();
        }
    }

    @Test
    void aTransactionThatRollsBackNeverBumpsTheCache() {
        TransactionSynchronizationManager.initSynchronization();
        try {
            invalidator.invalidateAfterCommit(USER);

            TransactionSynchronizationManager.getSynchronizations()
                    .forEach(sync -> sync.afterCompletion(TransactionSynchronization.STATUS_ROLLED_BACK));

            // The rows came back, so the answers that quoted them are still valid — retiring
            // their generation would be a needless (and dishonest) invalidation.
            verify(ai, never()).invalidateCache(USER);
            assertThat(registry.find(RagCacheInvalidator.INVALIDATED).counter()).isNull();
        } finally {
            TransactionSynchronizationManager.clearSynchronization();
        }
    }

    @Test
    void anAiServiceThatRefusesCannotUndoTheDelete() {
        doThrow(new IllegalStateException("ai-service down")).when(ai).invalidateCache(USER);

        assertThatCode(() -> invalidator.invalidateAfterCommit(USER)).doesNotThrowAnyException();

        // The delete already committed; a cache that did not learn about it expires on its
        // own TTL. The failure is counted and logged, never escalated to the reader.
        assertThat(count("failed")).isEqualTo(1.0);
        assertThat(count("requested")).isZero();
    }

    @Test
    void aRefusalInsideAfterCommitStillCannotUndoTheDelete() {
        doThrow(new IllegalStateException("ai-service down")).when(ai).invalidateCache(USER);
        TransactionSynchronizationManager.initSynchronization();
        try {
            invalidator.invalidateAfterCommit(USER);

            assertThatCode(this::commit).doesNotThrowAnyException();

            verify(ai).invalidateCache(USER);
            assertThat(count("failed")).isEqualTo(1.0);
        } finally {
            TransactionSynchronizationManager.clearSynchronization();
        }
    }

    @Test
    void aNullUserIsAnInertNoOp() {
        invalidator.invalidateAfterCommit(null);

        verify(ai, never()).invalidateCache(org.mockito.ArgumentMatchers.any());
        assertThat(registry.find(RagCacheInvalidator.INVALIDATED).counter()).isNull();
    }

    /** What the transaction manager does to the registered synchronizations on commit. */
    private void commit() {
        TransactionSynchronizationManager.getSynchronizations()
                .forEach(TransactionSynchronization::afterCommit);
    }

    private double count(String outcome) {
        Counter counter = registry.find(RagCacheInvalidator.INVALIDATED).tag("outcome", outcome)
                .counter();
        return counter == null ? 0.0 : counter.count();
    }
}
