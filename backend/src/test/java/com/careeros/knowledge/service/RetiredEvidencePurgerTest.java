package com.careeros.knowledge.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.inOrder;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.knowledge.repository.DocumentRepository;
import java.time.OffsetDateTime;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.InOrder;

/**
 * The audit record a delete leaves behind has a window (roadmap 44.3), and closing it is three
 * reads and a delete that have to happen in that order: the chunks can only be counted while
 * their rows are still there, and the keys can only be read while the rows still name them.
 *
 * <p>What the window does not do is decide on its own. A retired document a source row still
 * points at is left where it is and reported, because taking it would break that source's own
 * delete; and a pass that throws queues no reclaim, so a rolled-back purge cannot have taken a
 * file.
 */
class RetiredEvidencePurgerTest {

    private static final OffsetDateTime CUTOFF = OffsetDateTime.parse("2026-05-02T04:47:00Z");
    private static final String KEY = "a-user/uploads/a-blob.bin";

    private final DocumentRepository documents = mock(DocumentRepository.class);
    private final StoredObjectReclaimer reclaimer = mock(StoredObjectReclaimer.class);
    private final RetiredEvidencePurger purger =
            new RetiredEvidencePurger(documents, reclaimer);

    @BeforeEach
    void anAgedRetiredRowWithChunksAndAKey() {
        when(documents.countRetiredChunksBefore("retired", CUTOFF)).thenReturn(40L);
        when(documents.findRetiredFileKeysBefore("retired", CUTOFF)).thenReturn(List.of(KEY));
        when(documents.deleteRetiredBefore("retired", CUTOFF)).thenReturn(2);
        when(documents.countRetiredButStillNamedBefore("retired", CUTOFF)).thenReturn(0L);
    }

    @Test
    void theWindowIsRetiredStatusAndACutoffAndNothingElse() {
        RetiredEvidencePurger.Purge purge = purger.purgeBefore(CUTOFF);

        ArgumentCaptor<String> status = ArgumentCaptor.forClass(String.class);
        verify(documents).deleteRetiredBefore(status.capture(), eq(CUTOFF));
        assertThat(status.getValue()).isEqualTo("retired");

        // Live, pending and failed rows are nobody's window to close: only the status the delete
        // path wrote is aged out, and the row's last write is the retirement itself.
        assertThat(purge.documents()).isEqualTo(2);
    }

    @Test
    void theRowsAreJudgedBeforeTheyAreGone() {
        purger.purgeBefore(CUTOFF);

        // Counting chunks after the delete would answer zero every night, and reading the keys
        // afterwards would find no row left to name them: the cascade and the reclaim are both
        // judged from what the rows still were when the pass began.
        InOrder order = inOrder(documents);
        order.verify(documents).countRetiredChunksBefore("retired", CUTOFF);
        order.verify(documents).findRetiredFileKeysBefore("retired", CUTOFF);
        order.verify(documents).deleteRetiredBefore("retired", CUTOFF);
    }

    @Test
    void thePurgedRowsHandTheirKeysToTheSameReclaimADeleteWould() {
        purger.purgeBefore(CUTOFF);

        // 44.2's recovery route for a refused reclaim is the retired row naming its key, and this
        // pass deletes that row -- so the sweep asks the store, with the same two questions,
        // before the trail is burned.
        verify(reclaimer).reclaim(List.of(KEY));
    }

    @Test
    void itTellsTheSweepWhatTheWindowTook() {
        when(documents.countRetiredButStillNamedBefore("retired", CUTOFF)).thenReturn(3L);

        RetiredEvidencePurger.Purge purge = purger.purgeBefore(CUTOFF);

        assertThat(purge.documents()).isEqualTo(2);
        assertThat(purge.chunks()).isEqualTo(40L);
        assertThat(purge.leftNamed()).isEqualTo(3L);
    }

    @Test
    void aSourceStillNamingARetiredRowKeepsItOutOfThePurgeAndIntoTheLog() {
        RetiredEvidencePurger.Purge purge = purger.purgeBefore(CUTOFF);

        // The repository's own predicate is what leaves the row, so the purger's job is to ask
        // afterwards how many the window reached and the source spared -- and to say it plainly
        // rather than let a night that removed nothing look like a night with nothing to remove.
        assertThat(purge.leftNamed()).isZero();
        verify(documents).countRetiredButStillNamedBefore(anyString(), any());
    }

    @Test
    void aPassWithNoKeyedRowAsksNothingOfTheStore() {
        when(documents.findRetiredFileKeysBefore("retired", CUTOFF)).thenReturn(List.of());

        purger.purgeBefore(CUTOFF);

        // Text ingested inline has no object behind it: the pass still deletes rows and chunks,
        // and hands the reclaimer an empty list to do nothing with.
        verify(reclaimer).reclaim(List.of());
        verify(documents).deleteRetiredBefore("retired", CUTOFF);
    }

    @Test
    void aPurgeThatFailsQueuesNoReclaim() {
        when(documents.deleteRetiredBefore("retired", CUTOFF))
                .thenThrow(new IllegalStateException("deadlock on documents"));

        assertThatThrownBy(() -> purger.purgeBefore(CUTOFF)).isInstanceOf(IllegalStateException.class);

        // The transaction this pass runs in rolls back, so the rows and their chunks stay -- and
        // an object reclaimed against a purge that never happened would be a file destroyed by a
        // delete the reader still has.
        verify(reclaimer, never()).reclaim(any());
    }
}
