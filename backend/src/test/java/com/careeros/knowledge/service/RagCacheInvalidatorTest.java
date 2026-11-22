package com.careeros.knowledge.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.ai.AiServiceClient;
import com.careeros.queue.JobQueue;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.util.Map;
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
 *
 * <p>Epic 417 added the queue in front of the bump, and the mock answers the way a
 * disabled queue does — {@code enqueue} returns false — so every case below is the
 * pre-queue behaviour unless it says otherwise. That defaulting is the claim the epic
 * makes: the queue is an upgrade a caller does not have to know about.
 */
class RagCacheInvalidatorTest {

    private static final UUID USER = UUID.fromString("00000000-0000-0000-0000-0000000000aa");

    private AiServiceClient ai;
    private SimpleMeterRegistry registry;
    private JobQueue queue;
    private RagCacheInvalidator invalidator;

    @BeforeEach
    void setUp() {
        ai = mock(AiServiceClient.class);
        registry = new SimpleMeterRegistry();
        queue = mock(JobQueue.class);
        // The fleet says no, which is what a disabled queue or a refused write answers. The
        // cases below therefore take the inline path unless they overrule it themselves.
        when(queue.enqueue(any(), any())).thenReturn(false);
        invalidator = new RagCacheInvalidator(ai, registry, queue);
    }

    @Test
    void withNoActiveTransactionTheBumpRunsInline() {
        invalidator.invalidateAfterCommit(USER);

        verify(ai).invalidateCache(USER);
        assertThat(count("requested")).isEqualTo(1.0);
    }

    @Test
    void anEnqueuedInvalidationIsNotAlsoRunHere() {
        when(queue.enqueue(any(), any())).thenReturn(true);

        invalidator.invalidateAfterCommit(USER);

        // The stream took the job, so the fleet owns the bump. Doing it here as well would be
        // a second epoch for one delete -- harmless, but it would leave "the queue runs it"
        // untestable, because every path would bump no matter what the queue answered.
        verify(ai, never()).invalidateCache(USER);
        assertThat(registry.find(RagCacheInvalidator.INVALIDATED).counter()).isNull();
        // The field name is the whole wire contract between this producer and the handler.
        verify(queue).enqueue(RagCacheInvalidationJob.KIND,
                Map.of(RagCacheInvalidationJob.USER_FIELD, USER.toString()));
    }

    @Test
    void theQueueEntryIsHandedOverOnlyOnceTheDeleteIsDurable() {
        when(queue.enqueue(any(), any())).thenReturn(true);
        TransactionSynchronizationManager.initSynchronization();
        try {
            invalidator.invalidateAfterCommit(USER);

            // Epic 147's rule did not move just because the work left this process: an entry
            // the fleet can already read, for rows a transaction has not finished deciding, is
            // an invalidation of answers that are still valid.
            verify(queue, never()).enqueue(eq(RagCacheInvalidationJob.KIND), any());

            commit();

            verify(queue).enqueue(RagCacheInvalidationJob.KIND,
                    Map.of(RagCacheInvalidationJob.USER_FIELD, USER.toString()));
            verify(ai, never()).invalidateCache(USER);
        } finally {
            TransactionSynchronizationManager.clearSynchronization();
        }
    }

    @Test
    void aRollbackOffersTheJobToTheFleetEither() {
        when(queue.enqueue(any(), any())).thenReturn(true);
        TransactionSynchronizationManager.initSynchronization();
        try {
            invalidator.invalidateAfterCommit(USER);

            TransactionSynchronizationManager.getSynchronizations()
                    .forEach(sync -> sync.afterCompletion(TransactionSynchronization.STATUS_ROLLED_BACK));

            verify(queue, never()).enqueue(eq(RagCacheInvalidationJob.KIND), any());
            verify(ai, never()).invalidateCache(USER);
        } finally {
            TransactionSynchronizationManager.clearSynchronization();
        }
    }

    @Test
    void aBumpFromTheQueueCountsTheSameAsABumpFromThisThread() {
        // The handler's whole job is to call `bump`, so the meter that alarms on a forgotten
        // invalidation has to mean the same thing whichever door the bump came through.
        invalidator.bump(USER);

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
