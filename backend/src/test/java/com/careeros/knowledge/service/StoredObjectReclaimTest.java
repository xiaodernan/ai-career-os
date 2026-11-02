package com.careeros.knowledge.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.knowledge.repository.DocumentRepository;
import com.careeros.resume.repository.ResumeRepository;
import com.careeros.storage.StorageService;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;

/**
 * An upload stores one object and points two rows at it: the document the bytes were ingested into
 * and the resume that serves them as its original file. Deleting either row retires the copy, so
 * the object goes only with the last row that still names it -- and only once the rows that named it
 * are durably gone, because a delete whose file is already gone is not a delete that failed.
 */
class StoredObjectReclaimTest {

    private static final String KEY = "a-user/uploads/a-blob.bin";

    private DocumentRepository documents;
    private ResumeRepository resumes;
    private StorageService storage;
    private SimpleMeterRegistry registry;
    private StoredObjectReclaimer reclaimer;

    @BeforeEach
    void setUp() {
        documents = mock(DocumentRepository.class);
        resumes = mock(ResumeRepository.class);
        storage = mock(StorageService.class);
        registry = new SimpleMeterRegistry();
        reclaimer = new StoredObjectReclaimer(documents, resumes, storage, registry);
    }

    @Test
    void theLastRowToGoTakesTheObjectWithIt() {
        reclaimer.reclaim(List.of(KEY));

        verify(storage).delete(KEY);
        assertThat(count("deleted")).isEqualTo(1.0);
        assertThat(count("referenced")).isZero();
    }

    @Test
    void theRetiredRowIsTheOneExcludedFromTheQuestion() {
        reclaimer.reclaim(List.of(KEY));

        // The retired document keeps its key as the audit record. Asked without excluding it,
        // every reclaim would answer "still in use" and no object would ever go.
        ArgumentCaptor<String> excluded = ArgumentCaptor.forClass(String.class);
        verify(documents).existsByFileKeyAndStatusNot(eq(KEY), excluded.capture());
        assertThat(excluded.getValue()).isEqualTo("retired");
    }

    @Test
    void aResumeStillServingItsUploadKeepsTheFile() {
        when(resumes.existsBySourceFileKey(KEY)).thenReturn(true);

        reclaimer.reclaim(List.of(KEY));

        // Deleting the knowledge entry that was made from a resume's file stops the AI quoting it;
        // it does not take the original file off the resume's own page.
        verify(storage, never()).delete(anyString());
        assertThat(count("referenced")).isEqualTo(1.0);
    }

    @Test
    void aDocumentThatIsStillQuotableKeepsTheFile() {
        when(documents.existsByFileKeyAndStatusNot(KEY, "retired")).thenReturn(true);

        reclaimer.reclaim(List.of(KEY));

        verify(storage, never()).delete(anyString());
        assertThat(count("referenced")).isEqualTo(1.0);
    }

    @Test
    void aStoreThatRefusesLeavesTheDeleteStanding() {
        doThrow(new IllegalStateException("MinIO down")).when(storage).delete(KEY);

        assertThatCode(() -> reclaimer.reclaim(List.of(KEY))).doesNotThrowAnyException();

        // The rows are already gone and the reader's delete succeeded; a file the store would not
        // give back is counted, and the retired row still names its key so erasure can find it.
        assertThat(count("failed")).isEqualTo(1.0);
        assertThat(count("deleted")).isZero();
    }

    @Test
    void anInlineTextCopyNamesNoKeyAndAsksNothing() {
        reclaimer.reclaim(List.of());

        verify(documents, never()).existsByFileKeyAndStatusNot(anyString(), anyString());
        verify(storage, never()).delete(anyString());
        assertThat(registry.find(StoredObjectReclaimer.RECLAIMED).counter()).isNull();
    }

    @Test
    void aNullAndABlankKeyAreNotKeys() {
        List<String> keys = new ArrayList<>();
        keys.add(null);
        keys.add("  ");
        keys.add(KEY);

        reclaimer.reclaim(keys);

        verify(storage).delete(KEY);
        assertThat(count("deleted")).isEqualTo(1.0);
    }

    @Test
    void oneKeyIsJudgedOnceHoweverManyRowsNamedIt() {
        reclaimer.reclaim(List.of(KEY, KEY));

        verify(documents).existsByFileKeyAndStatusNot(KEY, "retired");
        verify(storage).delete(KEY);
        assertThat(count("deleted")).isEqualTo(1.0);
    }

    @Test
    void aDeleteInsideATransactionWaitsForThatTransactionToCommit() {
        TransactionSynchronizationManager.initSynchronization();
        try {
            reclaimer.reclaim(List.of(KEY));

            // A bundle restore deletes several rows inside one transaction it owns, and the key's
            // whole life may end in a transaction this reclaim cannot see the end of. Nothing is
            // judged while the rows are still unwritten.
            verify(storage, never()).delete(anyString());
            assertThat(count("deleted")).isZero();

            commit();

            verify(storage).delete(KEY);
            assertThat(count("deleted")).isEqualTo(1.0);
        } finally {
            TransactionSynchronizationManager.clearSynchronization();
        }
    }

    @Test
    void aTransactionThatRollsBackNeverTakesAFile() {
        TransactionSynchronizationManager.initSynchronization();
        try {
            reclaimer.reclaim(List.of(KEY));

            // The shape of a rollback: the synchronizations complete, and not one of them commits.
            // The rows came back, so the file they named has to still be there.
            TransactionSynchronizationManager.getSynchronizations()
                    .forEach(sync -> sync.afterCompletion(TransactionSynchronization.STATUS_ROLLED_BACK));

            verify(storage, never()).delete(anyString());
            assertThat(registry.find(StoredObjectReclaimer.RECLAIMED).counter()).isNull();
        } finally {
            TransactionSynchronizationManager.clearSynchronization();
        }
    }

    /** What the transaction manager does to the registered synchronizations when a commit lands. */
    private static void commit() {
        TransactionSynchronizationManager.getSynchronizations()
                .forEach(TransactionSynchronization::afterCommit);
    }

    private double count(String outcome) {
        Counter counter = registry.find(StoredObjectReclaimer.RECLAIMED).tag("outcome", outcome)
                .counter();
        return counter == null ? 0.0 : counter.count();
    }
}
