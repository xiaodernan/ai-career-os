package com.careeros.knowledge.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.ai.AiServiceClient;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.knowledge.entity.Document;
import com.careeros.knowledge.repository.DocumentRepository;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.time.Duration;
import java.time.OffsetDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.data.domain.Pageable;
import org.springframework.test.util.ReflectionTestUtils;

/**
 * Epic 418, offline: the pass that picks up the uploads a commit registered and the engine never
 * started, asked of the one decision that matters — which rows may be touched, and what happens
 * when the touch is refused, already owned, or spent.
 *
 * <p>The window, the claim and the limit are the whole behaviour, so each is a case here rather
 * than a constant to trust. The claim is mocked as the repository implements it — a row a sibling
 * moved is a row that answers 0 — because that statement's atomicity is
 * {@link IngestionRepairIT}'s question, asked against a real Postgres.
 */
class IngestionRepairServiceTest {

    private static final UUID USER = UUID.fromString("00000000-0000-0000-0000-000000000041");
    private static final UUID SOURCE = UUID.fromString("00000000-0000-0000-0000-000000000042");

    private DocumentRepository documents;
    private FileIngestService fileIngest;
    private AiServiceClient ai;
    private SimpleMeterRegistry registry;
    private IngestionRepairService service;

    @BeforeEach
    void setUp() {
        documents = mock(DocumentRepository.class);
        fileIngest = mock(FileIngestService.class);
        ai = mock(AiServiceClient.class);
        registry = new SimpleMeterRegistry();
        service = new IngestionRepairService(documents, fileIngest, ai,
                new IngestionRepairMetrics(registry), 30);
    }

    /** A row as the tick sees it after its own claim: the id is the generator's, the attempts are the claim's. */
    private static Document row(UUID id, String status, Integer attempts) {
        Document doc = new Document();
        ReflectionTestUtils.setField(doc, "id", id);
        doc.setUserId(USER);
        doc.setSourceId(SOURCE);
        doc.setStatus(status);
        doc.setMediaType("text/plain");
        doc.setContentHash("hash");
        Map<String, Object> meta = new HashMap<>();
        meta.put("kind", "note");
        if (attempts != null) {
            meta.put("repair", new HashMap<>(Map.of("attempts", attempts)));
        }
        doc.setMeta(meta);
        return doc;
    }

    private static UUID id() {
        return UUID.randomUUID();
    }

    private void board(Document... rows) {
        when(documents.findStuckForRepair(any(), any(), any())).thenReturn(List.of(rows));
    }

    private double count(String outcome) {
        return registry.get(IngestionRepairMetrics.REPAIRS).tag("outcome", outcome).counter().count();
    }

    @Test
    void aRowPastTheWindowIsOfferedBackToTheEngine() {
        UUID doc = id();
        board(row(doc, "pending", null));
        when(documents.claimForRepair(eq(doc), any(), any())).thenReturn(1);

        assertThat(service.sweep()).isEqualTo(1);

        verify(ai).ingestDocument(doc, USER);
        verify(fileIngest, never()).markFailed(any(), any());
        assertThat(count(IngestionRepairMetrics.REQUEUED)).isEqualTo(1.0);
        assertThat(count(IngestionRepairMetrics.EXHAUSTED)).isZero();
    }

    @Test
    void theWindowAndTheTwoStuckStatesAreWhatNarrowTheBoard() {
        ArgumentCaptor<List<String>> statuses = ArgumentCaptor.forClass(List.class);
        ArgumentCaptor<OffsetDateTime> cutoff = ArgumentCaptor.forClass(OffsetDateTime.class);
        ArgumentCaptor<Pageable> page = ArgumentCaptor.forClass(Pageable.class);

        service.sweep();

        verify(documents).findStuckForRepair(statuses.capture(), cutoff.capture(), page.capture());
        assertThat(statuses.getValue()).containsExactly("pending", "indexing");
        long ageMinutes = Duration.between(cutoff.getValue(), OffsetDateTime.now()).toMinutes();
        assertThat(ageMinutes).isEqualTo(30);
        assertThat(page.getValue().getPageSize()).isEqualTo(IngestionRepairService.BATCH);
        assertThat(page.getValue().getOffset()).isZero();
    }

    @Test
    void aRowASiblingClaimedFirstIsLeftAlone() {
        UUID doc = id();
        board(row(doc, "indexing", null));
        when(documents.claimForRepair(eq(doc), any(), any())).thenReturn(0);

        assertThat(service.sweep()).isZero();

        verify(ai, never()).ingestDocument(any(), any());
        verify(fileIngest, never()).markFailed(any(), any());
        assertThat(count(IngestionRepairMetrics.CONTENDED)).isEqualTo(1.0);
    }

    @Test
    void aRefusedOfferStaysStuckRatherThanTurningFailed() {
        // An engine that is restarting is a reason to try again, and the row's own state is what
        // makes the next window try. The repair writes no verdict the request thread would have
        // written, because nobody is waiting on this answer.
        UUID doc = id();
        board(row(doc, "pending", null));
        when(documents.claimForRepair(eq(doc), any(), any())).thenReturn(1);
        when(ai.ingestDocument(eq(doc), eq(USER)))
                .thenThrow(new ApiException(ApiErrorCode.AI_SERVICE_UNAVAILABLE, "ai-service is down"));

        assertThat(service.sweep()).isZero();

        verify(fileIngest, never()).markFailed(any(), any());
        assertThat(count(IngestionRepairMetrics.REFUSED)).isEqualTo(1.0);
    }

    @Test
    void aSpentLimitIsAVerdictAndNotAFourthSpinner() {
        UUID doc = id();
        board(row(doc, "indexing", IngestionRepairService.MAX_OFFERS));

        assertThat(service.sweep()).isZero();

        verify(ai, never()).ingestDocument(any(), any());
        // The verdict reads the count and claims nothing: a row that was offered three times says
        // three, and the tick that gave up does not add a fourth offer nobody made.
        verify(documents, never()).claimForRepair(any(), any(), any());
        verify(fileIngest).markFailed(eq(new FileIngestService.Persisted(SOURCE, doc)),
                eq("ingestion never landed after " + IngestionRepairService.MAX_OFFERS + " offers"));
        assertThat(count(IngestionRepairMetrics.EXHAUSTED)).isEqualTo(1.0);
    }

    @Test
    void theBoardIsReadOnceRatherThanRePolledRowByRow() {
        // One select, then a claim and a POST per row. A pass that re-read each candidate after
        // claiming it would be a second query per document on the same clock that exists because
        // nobody else looks at these rows, and the count it needs is already in the row it hold.
        UUID doc = id();
        board(row(doc, "pending", null));
        when(documents.claimForRepair(eq(doc), any(), any())).thenReturn(1);

        assertThat(service.sweep()).isEqualTo(1);

        verify(documents, never()).findById(any());
    }

    @Test
    void oneRefusalDoesNotCostTheRestOfTheBoardTheirTick() {
        UUID first = id();
        UUID second = id();
        board(row(first, "pending", null), row(second, "indexing", null));
        when(documents.claimForRepair(any(), any(), any())).thenReturn(1);
        when(ai.ingestDocument(eq(first), eq(USER)))
                .thenThrow(new ApiException(ApiErrorCode.AI_SERVICE_UNAVAILABLE, "no answer"));

        assertThat(service.sweep()).isEqualTo(1);

        verify(ai).ingestDocument(second, USER);
        assertThat(count(IngestionRepairMetrics.REFUSED)).isEqualTo(1.0);
        assertThat(count(IngestionRepairMetrics.REQUEUED)).isEqualTo(1.0);
    }

    @Test
    void anEmptyBoardStillMovesTheHeartbeat() {
        // The alarm reads this gauge, so it has to be able to tell a quiet install from a stopped
        // clock: a tick that found nothing is a tick that ran.
        assertThat(service.sweep()).isZero();

        double ageSeconds = System.currentTimeMillis() / 1000.0
                - registry.get(IngestionRepairMetrics.LAST_TICK).gauge().value();
        assertThat(ageSeconds).isLessThan(60);
    }

    @Test
    void theFourOutcomesAreOnTheScrapeBeforeAnythingHappens() {
        // Registered at boot rather than on first use: a rate() over a tag never yet seen answers
        // nothing, and a clock that has never been refused would then look healthier on the
        // dashboard than one that is refusing.
        for (String outcome : List.of(IngestionRepairMetrics.REQUEUED, IngestionRepairMetrics.REFUSED,
                IngestionRepairMetrics.CONTENDED, IngestionRepairMetrics.EXHAUSTED)) {
            assertThat(count(outcome)).isZero();
        }
    }

    @Test
    void aRowWithNoRepairKeyIsOfferedAsTheFirstTimeItIs() {
        // No key is not zero offers waiting to be spent: it means nothing has ever been offered,
        // so this tick's POST is the first of the three the limit allows. Reading the absence as
        // already-spent would fail an upload on its first stumble.
        UUID doc = id();
        board(row(doc, "pending", null));
        when(documents.claimForRepair(eq(doc), any(), any())).thenReturn(1);

        assertThat(service.sweep()).isEqualTo(1);

        verify(ai).ingestDocument(doc, USER);
        verify(fileIngest, never()).markFailed(any(), any());
    }
}
