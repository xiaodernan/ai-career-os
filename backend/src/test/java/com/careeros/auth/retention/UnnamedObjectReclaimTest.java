package com.careeros.auth.retention;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.inOrder;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.knowledge.repository.DocumentRepository;
import com.careeros.resume.repository.ResumeRepository;
import com.careeros.storage.StorageService;
import com.careeros.storage.StorageService.StoredObject;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.time.OffsetDateTime;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.InOrder;

/**
 * Roadmap 48.2: the bucket holds objects because a request stored bytes, and the row that would
 * have named them never arrived -- a rollback between the two writes, a crash, or a reclaim the
 * store refused before the row that held the claim was purged. Nothing else in the install ever
 * looks at those bytes, because every other path starts from a row.
 *
 * <p>So the pass is the one delete in this codebase whose input is the store rather than the
 * database, and that inverts what it has to prove. The tests below are about three inversions:
 * the reads go in the order that makes a live upload un-touchable (listing first, rows after);
 * the subtraction is wider than 44.2's, because a retired row's key is a claim here even though it
 * is not a reason to keep bytes when a reader deletes; and a store that refuses to answer is a
 * pass that reclaims nothing rather than a bucket that holds nothing.
 */
class UnnamedObjectReclaimTest {

    private static final OffsetDateTime CUTOFF = OffsetDateTime.parse("2026-10-29T04:47:00Z");
    private static final String ORPHAN = "a-user/uploads/a-blob.bin";
    private static final String NAMED = "b-user/uploads/b-blob.bin";
    private static final String RESUMED = "c-user/resumes/c-blob.pdf";
    private static final String YOUNG = "d-user/uploads/d-blob.bin";

    private DocumentRepository documents;
    private ResumeRepository resumes;
    private StorageService storage;
    private SimpleMeterRegistry registry;
    private UnnamedObjectReclaimer reclaimer;

    @BeforeEach
    void setUp() {
        documents = mock(DocumentRepository.class);
        resumes = mock(ResumeRepository.class);
        storage = mock(StorageService.class);
        registry = new SimpleMeterRegistry();
        reclaimer = new UnnamedObjectReclaimer(documents, resumes, storage, registry);

        when(storage.list()).thenReturn(List.of(
                object(ORPHAN, CUTOFF.minusDays(1)),
                object(NAMED, CUTOFF.minusDays(1)),
                object(RESUMED, CUTOFF.minusDays(1)),
                object(YOUNG, CUTOFF.plusHours(1))));
        when(documents.findAllFileKeys()).thenReturn(List.of(NAMED));
        when(resumes.findAllSourceFileKeys()).thenReturn(List.of(RESUMED));
    }

    @Test
    void anObjectNoRowNamesAndOlderThanTheWindowIsReclaimedAndTheRestAreLeft() {
        UnnamedObjectReclaimer.Reclaim reclaim = reclaimer.reclaimBefore(CUTOFF);

        verify(storage).delete(ORPHAN);
        verify(storage, never()).delete(NAMED);
        verify(storage, never()).delete(RESUMED);
        verify(storage, never()).delete(YOUNG);
        // The four verdicts are the whole listing, so the reading checks its own arithmetic: an
        // object that left the pass unjudged shows up here as a sum that does not close. Two of
        // the four are named -- one by each of the two tables the key columns live in.
        assertThat(reclaim).isEqualTo(new UnnamedObjectReclaimer.Reclaim(4, 2, 1, 1, 0));
        assertThat(reclaim.listed())
                .isEqualTo(reclaim.named() + reclaim.young() + reclaim.deleted() + reclaim.failed());
    }

    @Test
    void theListingIsTakenBeforeTheRowsBecauseTheOtherOrderIsAWindowThatCannotClose() {
        reclaimer.reclaimBefore(CUTOFF);

        // Read the rows first and an upload that stored its bytes, paused, and committed its row
        // during the pass would find its file judged by a table read taken before the row existed.
        // Listing first means every key the listing can show was stored before it ran, and any row
        // committing after that is in the set the subtraction uses.
        InOrder order = inOrder(storage, documents, resumes);
        order.verify(storage).list();
        order.verify(documents).findAllFileKeys();
        order.verify(resumes).findAllSourceFileKeys();
    }

    @Test
    void aRetiredRowsKeyIsAClaimHereEvenThoughItIsNotOneIn442sQuestion() {
        // The document table's read has no status filter, so the retired row below names its key
        // exactly as a ready one does. Asked the way the delete path asks it, every object a reader
        // deleted would be reclaimable the next night -- including the ones whose reclaim the store
        // refused and whose audit record is the only thing left pointing at them.
        when(documents.findAllFileKeys()).thenReturn(List.of(NAMED, "retired-user/uploads/x.bin"));
        when(storage.list()).thenReturn(List.of(
                object(NAMED, CUTOFF.minusDays(1)),
                object("retired-user/uploads/x.bin", CUTOFF.minusDays(1))));

        UnnamedObjectReclaimer.Reclaim reclaim = reclaimer.reclaimBefore(CUTOFF);

        verify(storage, never()).delete(anyString());
        assertThat(reclaim.named()).isEqualTo(2);
        assertThat(reclaim.deleted()).isZero();
    }

    @Test
    void anObjectYoungerThanTheCutoffIsLeftAloneEvenThoughNoRowNamesIt() {
        UnnamedObjectReclaimer.Reclaim reclaim = reclaimer.reclaimBefore(CUTOFF);

        // This is the window's whole job: the bytes an upload stored a moment ago have no row yet
        // for the same reason an orphan has no row -- the write is still on its way.
        verify(storage, never()).delete(YOUNG);
        assertThat(reclaim.young()).isEqualTo(1);
        assertThat(count(UnnamedObjectReclaimer.YOUNG)).isEqualTo(1.0);
    }

    @Test
    void anObjectExactlyAtTheCutoffIsYoungBecauseOnlyStrictlyOlderIsGarbage() {
        when(storage.list()).thenReturn(List.of(object(ORPHAN, CUTOFF)));

        UnnamedObjectReclaimer.Reclaim reclaim = reclaimer.reclaimBefore(CUTOFF);

        // The boundary is judged toward keeping the bytes. A store whose clock runs ahead of this
        // one's produces an object younger than it is, and the cost of that direction is a week of
        // storage; the other direction costs a reader their upload.
        assertThat(reclaim.young()).isEqualTo(1);
        assertThat(reclaim.deleted()).isZero();
        verify(storage, never()).delete(anyString());
    }

    @Test
    void anObjectTheStoreCannotDateArrivesYoungAndStays() {
        // 48.1 dated an undated object at the moment the listing read it, precisely for this pass:
        // a missing timestamp keeps the bytes instead of making the object the oldest thing there.
        when(storage.list()).thenReturn(List.of(object(ORPHAN, OffsetDateTime.now())));

        UnnamedObjectReclaimer.Reclaim reclaim = reclaimer.reclaimBefore(CUTOFF.minusYears(1));

        assertThat(reclaim.young()).isEqualTo(1);
        verify(storage, never()).delete(anyString());
    }

    @Test
    void aListingThatRefusesIsNotABucketThatIsEmpty() {
        when(storage.list()).thenThrow(new ApiException(ApiErrorCode.STORAGE_READ_FAILED,
                "Object storage read failed"));

        assertThatThrownBy(() -> reclaimer.reclaimBefore(CUTOFF)).isInstanceOf(ApiException.class);

        // The throw goes out on purpose: the phase above it is the one that says "the bucket was
        // not swept", and nothing here may delete on the strength of a read that never happened.
        verify(storage, never()).delete(anyString());
        verify(documents, never()).findAllFileKeys();
        assertThat(count(UnnamedObjectReclaimer.DELETED)).isZero();
        // And the night says so on a meter, not only in the log. The sweep's clock keeps moving
        // through a refused listing -- the pass finished, its other phases ran -- so without this
        // reading the install's only sign that the bucket went unswept would be a WARN line no
        // dashboard reads.
        assertThat(readCount(UnnamedObjectReclaimer.REFUSED)).isEqualTo(1.0);
        assertThat(readCount(UnnamedObjectReclaimer.LISTED)).isZero();
    }

    @Test
    void anAnsweredListingIsCountedAsOneNightAndNotAsTheObjectsItShowed() {
        reclaimer.reclaimBefore(CUTOFF);

        // One reading per pass, not per object: the alert is about a night that could not ask, and
        // a count that moved with the bucket's size would page harder the longer the install ran.
        assertThat(readCount(UnnamedObjectReclaimer.LISTED)).isEqualTo(1.0);
        assertThat(readCount(UnnamedObjectReclaimer.REFUSED)).isZero();
    }

    @Test
    void oneRefusedDeleteDoesNotStopTheObjectsBehindIt() {
        when(storage.list()).thenReturn(List.of(
                object("first.bin", CUTOFF.minusDays(1)),
                object("second.bin", CUTOFF.minusDays(1)),
                object("third.bin", CUTOFF.minusDays(1))));
        doThrow(new IllegalStateException("the store refused"))
                .when(storage).delete("second.bin");

        UnnamedObjectReclaimer.Reclaim reclaim = reclaimer.reclaimBefore(CUTOFF);

        verify(storage).delete("first.bin");
        verify(storage).delete("third.bin");
        assertThat(reclaim.deleted()).isEqualTo(2);
        assertThat(reclaim.failed()).isEqualTo(1);
        assertThat(count(UnnamedObjectReclaimer.FAILED)).isEqualTo(1.0);
    }

    @Test
    void aKeyTwoTablesShareIsJudgedOnceBecauseTheListingShowsOneObject() {
        when(documents.findAllFileKeys()).thenReturn(List.of(NAMED, ORPHAN));
        when(resumes.findAllSourceFileKeys()).thenReturn(List.of(ORPHAN, RESUMED));

        UnnamedObjectReclaimer.Reclaim reclaim = reclaimer.reclaimBefore(CUTOFF);

        verify(storage, never()).delete(ORPHAN);
        assertThat(reclaim.named()).isEqualTo(3);
        assertThat(reclaim.deleted()).isZero();
    }

    @Test
    void anEmptyBucketLeavesAWholePassWithNothingToJudge() {
        when(storage.list()).thenReturn(List.of());

        UnnamedObjectReclaimer.Reclaim reclaim = reclaimer.reclaimBefore(CUTOFF);

        assertThat(reclaim).isEqualTo(new UnnamedObjectReclaimer.Reclaim(0, 0, 0, 0, 0));
        verify(storage, never()).delete(anyString());
    }

    @Test
    void eachVerdictMovesItsOwnCounterAndNoOther() {
        reclaimer.reclaimBefore(CUTOFF);

        assertThat(count(UnnamedObjectReclaimer.NAMED)).isEqualTo(2.0);
        assertThat(count(UnnamedObjectReclaimer.YOUNG)).isEqualTo(1.0);
        assertThat(count(UnnamedObjectReclaimer.DELETED)).isEqualTo(1.0);
        assertThat(count(UnnamedObjectReclaimer.FAILED)).isZero();
    }

    private static StoredObject object(String key, OffsetDateTime lastModified) {
        return new StoredObject(key, lastModified, 12L);
    }

    private double count(String outcome) {
        Counter counter = counter(outcome);
        return counter == null ? 0.0 : counter.count();
    }

    private Counter counter(String outcome) {
        return registry.find(UnnamedObjectReclaimer.JUDGED).tag("outcome", outcome).counter();
    }

    private double readCount(String outcome) {
        Counter counter = registry.find(UnnamedObjectReclaimer.READS).tag("outcome", outcome).counter();
        return counter == null ? 0.0 : counter.count();
    }
}
