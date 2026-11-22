package com.careeros.knowledge.service;

import static org.assertj.core.api.Assertions.assertThat;

import com.careeros.ApiIntegrationTest;
import com.careeros.knowledge.repository.DocumentRepository;
import io.micrometer.core.instrument.MeterRegistry;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.PageRequest;
import org.springframework.jdbc.core.JdbcTemplate;

/**
 * Epic 418's repair clock measured against the schema Flyway built.
 *
 * <p>The unit tests pin what the pass decides; three things here can only be answered by a real
 * Postgres. The claim has to be the deduplication it claims to be — one statement that tests
 * {@code updated_at} and moves it, so a sibling arriving second reads 0 — and the only way to see
 * that is to run it twice against the same row. The attempt count has to land in {@code meta.repair}
 * without disturbing the key that created the row, which is a jsonb question, not a Java one. And
 * the window's predicate has to agree with the column the trigger writes: {@code touch_updated_at}
 * re-ages every UPDATE, so a claim also closes the window around the row it just offered, which is
 * what stops one document being re-offered on every tick forever.
 *
 * <p>Age is written at insert, never by an update, for the same reason (see
 * {@link com.careeros.auth.retention.RetiredEvidencePurgeIT}), and the shipped clock is pinned
 * inert for the suite in {@link com.careeros.AbstractIntegrationTest}. This pass builds its own
 * service so the window under test is the measurement's own value rather than the context's, and
 * clears the board first: the sweep is fleet-wide by design, so a count of what it offered is only
 * readable when the only stuck rows on it are the ones this method wrote.
 */
class IngestionRepairIT extends ApiIntegrationTest {

    private static final int PAST = 400;
    // The sweep is fleet-wide, so the board is cleared by the two statuses rather than by age: an
    // age clause here would be a second copy of the window the clock owns, and a row that is young
    // only stops the pass from offering it, it does not stop it from confusing a later count.
    private static final String STUCK_ROWS = "status in ('pending', 'indexing')";

    @Autowired
    private JdbcTemplate jdbc;

    @Autowired
    private DocumentRepository documents;

    @Autowired
    private FileIngestService fileIngest;

    @Autowired
    private IngestionRepairMetrics metrics;

    @Autowired
    private MeterRegistry registry;

    private UUID userId;
    private IngestionRepairService repair;

    @BeforeEach
    void anAccountAClockWithItsOwnWindowAndAnEmptyBoard() throws Exception {
        String email = "repair-" + UUID.randomUUID() + "@example.com";
        register(email);
        userId = jdbc.queryForObject("select id from users where email = ?", UUID.class, email);
        repair = new IngestionRepairService(documents, fileIngest, ai, metrics, 30);
        // Sources name documents and the foreign key restricts, so the board is cleared in that
        // order. Chunks go with the document on their own cascade.
        jdbc.update("delete from knowledge_sources where document_id in"
                + " (select id from documents where " + STUCK_ROWS + ")");
        jdbc.update("delete from documents where " + STUCK_ROWS);
    }

    @Test
    @DisplayName("an upload that never got its POST is offered, counted, and re-aged by the claim")
    void theClaimOffersAndArmsTheWindowAgain() {
        UUID doc = insertRow("pending", PAST, null);
        double requeued = count(IngestionRepairMetrics.REQUEUED);

        assertThat(repair.sweep()).isEqualTo(1);
        assertThat(ai.calls).containsExactly("ingestDocument");
        assertThat(attempts(doc)).isEqualTo(1);
        // The rest of the creator's jsonb is untouched: the count is a guest in meta, not a
        // rewrite of it.
        assertThat(meta(doc)).contains("\"kind\": \"note\"");
        assertThat(count(IngestionRepairMetrics.REQUEUED)).isEqualTo(requeued + 1.0);

        // The claim moved updated_at, so the row is inside the window again and the next tick has
        // nothing to say about it until the window really has passed. Without this the same
        // document would be offered every ten minutes whatever the engine does about the offer.
        assertThat(repair.sweep()).isZero();
        assertThat(ai.calls).hasSize(1);
        assertThat(attempts(doc)).isEqualTo(1);
    }

    @Test
    @DisplayName("the second claim of one row is refused by the row itself")
    void oneRowIsHandedToOneReplica() {
        UUID doc = insertRow("pending", PAST, null);
        OffsetDateTime cutoff = OffsetDateTime.now().minusMinutes(30);

        assertThat(documents.claimForRepair(doc, IngestionRepairService.STUCK, cutoff)).isEqualTo(1);
        // The same statement, the same cutoff, as the sibling that arrived a moment later:
        // Postgres re-evaluates the predicate on the new row version and finds the row no longer
        // stuck-old. This is the whole deduplication — no lease, no queue, no second writer.
        assertThat(documents.claimForRepair(doc, IngestionRepairService.STUCK, cutoff)).isZero();
        assertThat(attempts(doc)).isEqualTo(1);
    }

    @Test
    @DisplayName("a claim never moves a row the window does not cover or the status does not name")
    void thePredicateIsTheWholeGate() {
        UUID fresh = insertRow("pending", 0, null);
        UUID ready = insertRow("ready", PAST, null);
        UUID retired = insertRow("retired", PAST, null);
        UUID failed = insertRow("failed", PAST, null);

        assertThat(repair.sweep()).isZero();
        assertThat(ai.calls).isEmpty();

        for (UUID row : List.of(fresh, ready, retired, failed)) {
            assertThat(attempts(row)).isNull();
        }
        // 44.3 owns a retired row: the purge is what closes it, and a repair clock that claimed it
        // would re-open a deletion the reader already made.
        assertThat(status(retired)).isEqualTo("retired");
        assertThat(status(failed)).isEqualTo("failed");
    }

    @Test
    @DisplayName("the fourth look at a document writes a verdict instead of another spinner")
    void aSpentLimitFailsThePairWithAReason() {
        UUID source = insertSource();
        UUID doc = insertRow("pending", PAST, IngestionRepairService.MAX_OFFERS, source);
        double exhausted = count(IngestionRepairMetrics.EXHAUSTED);

        assertThat(repair.sweep()).isZero();
        assertThat(ai.calls).doesNotContain("ingestDocument");

        assertThat(status(doc)).isEqualTo("failed");
        assertThat(jdbc.queryForObject("select error from documents where id = ?", String.class, doc))
                .isEqualTo("ingestion never landed after " + IngestionRepairService.MAX_OFFERS
                        + " offers");
        // The verdict tick claims nothing, so the number the reader sees is the POSTs really made
        // rather than one more than the engine was ever asked for.
        assertThat(attempts(doc)).isEqualTo(IngestionRepairService.MAX_OFFERS);
        // The source moves with it, because the list the reader sees is the source's: a document
        // that failed silently under a source still saying "ingesting" is the lie this epic is about.
        assertThat(jdbc.queryForObject("select status from knowledge_sources where id = ?",
                String.class, source)).isEqualTo("failed");
        assertThat(count(IngestionRepairMetrics.EXHAUSTED)).isEqualTo(exhausted + 1.0);
    }

    @Test
    @DisplayName("an engine that refuses the offer leaves the row stuck rather than failed")
    void aRefusalIsAReasonToTryAgainNotToStop() {
        UUID doc = insertRow("pending", PAST, null);
        double refused = count(IngestionRepairMetrics.REFUSED);
        ai.failIngest = true;

        assertThat(repair.sweep()).isZero();

        // The request thread marks a trigger failure failed because a reader is waiting on an
        // answer. Nobody is waiting here, so the row keeps its retryable state and spends one of
        // its three offers instead of losing all of them.
        assertThat(status(doc)).isEqualTo("pending");
        assertThat(attempts(doc)).isEqualTo(1);
        assertThat(count(IngestionRepairMetrics.REFUSED)).isEqualTo(refused + 1.0);
    }

    @Test
    @DisplayName("one tick looks at a bounded board, oldest first")
    void theBoardIsNarrowedAndOrdered() {
        UUID older = insertRow("pending", PAST, null);
        UUID younger = insertRow("indexing", 200, null);
        OffsetDateTime cutoff = OffsetDateTime.now().minusMinutes(30);

        List<UUID> page = documents
                .findStuckForRepair(IngestionRepairService.STUCK, cutoff, PageRequest.of(0, 1))
                .stream().map(row -> row.getId()).toList();

        // The page's contract is which row a one-row tick spends its offer on: the upload that has
        // waited longest, not whichever the heap hands over first.
        assertThat(page).containsExactly(older);

        assertThat(repair.sweep()).isEqualTo(2);
        assertThat(ai.calls).hasSize(2);
        assertThat(attempts(older)).isEqualTo(1);
        assertThat(attempts(younger)).isEqualTo(1);
    }

    @Test
    @DisplayName("the repair clock's index is the one the sweep asks for")
    void thePartialIndexShipped() {
        String definition = jdbc.queryForObject(
                "select indexdef from pg_indexes where tablename = 'documents'"
                        + " and indexname = 'idx_docs_stuck_ingest'", String.class);

        // A per-tick scan of a documents table every install grows forever is the cost this
        // migration exists to avoid, and the predicate is what keeps the ready rows -- all of
        // them, in any real install -- out of the index altogether.
        assertThat(definition)
                .contains("updated_at")
                .contains("'pending'")
                .contains("'indexing'")
                .contains("status");
    }

    private UUID insertSource() {
        UUID id = UUID.randomUUID();
        jdbc.update("insert into knowledge_sources (id, user_id, kind, title, status)"
                        + " values (?, ?, ?, ?, ?)", id, userId, "note", "a stranded upload",
                "ingesting");
        return id;
    }

    private UUID insertRow(String status, int ageDays, Integer attempts) {
        return insertRow(status, ageDays, attempts, insertSource());
    }

    private UUID insertRow(String status, int ageDays, Integer attempts, UUID sourceId) {
        UUID id = UUID.randomUUID();
        OffsetDateTime aged = OffsetDateTime.now().minusDays(ageDays);
        String meta = attempts == null ? "{\"kind\": \"note\"}"
                : "{\"kind\": \"note\", \"repair\": {\"attempts\": " + attempts + "}}";
        jdbc.update("insert into documents (id, user_id, source_id, file_key, media_type, title,"
                        + " content_hash, status, meta, created_at, updated_at)"
                        + " values (?, ?, ?, ?, ?, ?, ?, ?, ?::jsonb, ?, ?)",
                id, userId, sourceId, "repair/uploads/file.txt", "text/plain", "a stranded upload",
                "hash-" + id, status, meta, aged, aged);
        // The back-pointer is the second statement, not the first: documents' row has to exist
        // before a non-deferred commit can name it, which is the shape FileIngestService.persistRows
        // writes in.
        jdbc.update("update knowledge_sources set document_id = ? where id = ?", id, sourceId);
        return id;
    }

    private String status(UUID id) {
        return jdbc.queryForObject("select status from documents where id = ?", String.class, id);
    }

    private String meta(UUID id) {
        return jdbc.queryForObject("select meta::text from documents where id = ?", String.class, id);
    }

    private Integer attempts(UUID id) {
        List<Integer> rows = jdbc.query("select (meta #>> '{repair,attempts}')::int from documents"
                + " where id = ?", (rs, n) -> rs.getObject(1, Integer.class), id);
        return rows.isEmpty() ? null : rows.get(0);
    }

    private double count(String outcome) {
        return registry.get(IngestionRepairMetrics.REPAIRS).tag("outcome", outcome).counter().count();
    }
}
