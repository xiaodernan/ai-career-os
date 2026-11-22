package com.careeros.knowledge.service;

import com.careeros.ai.AiServiceClient;
import com.careeros.common.Paging;
import com.careeros.knowledge.entity.Document;
import com.careeros.knowledge.repository.DocumentRepository;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

/**
 * Picks up the uploads that were registered and never ingested (Epic 418).
 *
 * <p>The hole is a gap of milliseconds, and it is not hypothetical. {@link FileIngestService}
 * commits the source and document rows in one transaction — {@code 'ingesting'} and
 * {@code 'pending'} — and <em>then</em>, outside it, tells the engine to start. That ordering is
 * deliberate (a model call must not hold a transaction open), and it leaves two states a
 * document can sit in forever: it never got its POST, because the replica died or was drained in
 * the gap after the commit; or it got the POST, and the engine's own process died mid-task, so no
 * exception ever arrived to mark anything failed. Nothing in the install looked at either row
 * again. The reader's page kept drawing "ingesting" over a document that was, at that point,
 * nobody's job — the same shape as the read-failure defect this project keeps meeting, where the
 * answer to "where is my upload" is silence rather than a verdict.
 *
 * <p>So this is the pass that asks the question. A row in {@code 'pending'} or {@code 'indexing'}
 * whose {@code updated_at} is older than {@code careeros.ingestion.repair.window-minutes} is
 * re-offered to the engine, which is safe to do as many times as needed: the pipeline re-reads the
 * stored bytes, and its own chunk write deletes the document's chunks before it stores the new
 * set, so a second run leaves exactly one index rather than two.
 *
 * <p>The window is the whole safety of that claim. A 300-page PDF that is genuinely still being
 * embedded also reads {@code 'indexing'}, and a clock that mistook it for a corpse would start a
 * second ingestion of the same document; two writers deleting and inserting the same ordinals can
 * leave both sets behind. The window is therefore a floor on how long real work may take, not a
 * tuning convenience — and it is the only knob this class exposes. The offer limit and the
 * per-tick batch are module constants, for the reason the task bus gives for its own: a knob
 * nobody would read is a knob that does nothing, and an operator retunes the window before they
 * retune either of those.
 *
 * <p>Three offers, then a verdict. A document the engine keeps refusing is not a job this clock
 * can rescue, and a row re-offered every ten minutes for a month is a different shape of the same
 * lie: "ingesting" for a thing that is never coming. The count lives in
 * {@code meta.repair.attempts}, a nested key because the rest of that column belongs to whoever
 * created the row (the kind, and for a pasted note its inline text), and it is the number of POSTs
 * this clock actually made — the tick that writes the verdict reads the count and claims nothing,
 * so a reader who asks how many times the upload was retried gets a number that is not one too
 * many. The last word is {@link FileIngestService#markFailed} — the call the request thread
 * already makes, which moves the source and the document together, records the reason an operator
 * can read, and refuses to overwrite a retirement.
 *
 * <p>No fleet lease guards this clock, though Epic 169–171 established the lease as the shape for
 * a sweep. The lease exists to stop N replicas doing the same work N times, and the claim in
 * {@link DocumentRepository#claimForRepair} already does that in the database: it tests
 * {@code updated_at} and moves it in one statement, so a losing replica reads 0 and steps on. A
 * lease would guard work the row has already refused to hand out, and correctness in a mixed
 * deployment — queue off, queue on, Redis unreachable — must not depend on which is set.
 *
 * <p>Every document's failure is that document's own. One row whose POST throws is logged, counted
 * {@code refused}, and left for the next window; the tick finishes the rows after it and moves the
 * heartbeat whether or not anything was stuck.
 */
@Service
public class IngestionRepairService {

    private static final Logger log = LoggerFactory.getLogger(IngestionRepairService.class);

    /** The two states that mean nobody is working on this row any more. */
    static final List<String> STUCK = List.of("pending", "indexing");

    /** Offers a document gets before the clock records a verdict instead of trying again. */
    static final int MAX_OFFERS = 3;

    /** Rows one tick may look at, oldest first; the rest wait for the next tick. */
    static final int BATCH = 25;

    private final DocumentRepository documents;
    private final FileIngestService fileIngest;
    private final AiServiceClient ai;
    private final IngestionRepairMetrics metrics;
    private final int windowMinutes;

    public IngestionRepairService(DocumentRepository documents, FileIngestService fileIngest,
                                  AiServiceClient ai, IngestionRepairMetrics metrics,
                                  @Value("${careeros.ingestion.repair.window-minutes:30}") int windowMinutes) {
        this.documents = documents;
        this.fileIngest = fileIngest;
        this.ai = ai;
        this.metrics = metrics;
        this.windowMinutes = windowMinutes;
    }

    /**
     * One tick. Returns the documents handed back to the engine, which is what the log line and
     * the handler's answer are about; a tick that found nothing returns zero and still counts as
     * a tick that ran.
     */
    public int sweep() {
        OffsetDateTime cutoff = OffsetDateTime.now(ZoneOffset.UTC).minusMinutes(windowMinutes);
        int offered = 0;
        for (Document candidate : documents.findStuckForRepair(STUCK, cutoff, Paging.first(BATCH))) {
            if (offer(candidate, cutoff)) {
                offered++;
            }
        }
        metrics.tickFinished();
        return offered;
    }

    /** True when this tick ended by giving the document back to the engine. */
    private boolean offer(Document candidate, OffsetDateTime cutoff) {
        UUID id = candidate.getId();
        int made = offersOf(candidate);
        if (made >= MAX_OFFERS) {
            // Not claimed: a verdict spends no offer, and the row leaves the board the moment the
            // status moves, so the count a reader sees is the number of POSTs actually made.
            fileIngest.markFailed(new FileIngestService.Persisted(candidate.getSourceId(), id),
                    "ingestion never landed after " + made + " offers");
            metrics.record(IngestionRepairMetrics.EXHAUSTED);
            log.warn("document {} was offered {} time(s) and never ingested; recorded as failed", id, made);
            return false;
        }
        if (documents.claimForRepair(id, STUCK, cutoff) == 0) {
            // Another replica moved the row first — or the row left the statuses this clock reads,
            // which is the same answer from the database. Its POST is the one that will land;
            // re-offering here would be a second writer on one index.
            metrics.record(IngestionRepairMetrics.CONTENDED);
            return false;
        }
        try {
            ai.ingestDocument(id, candidate.getUserId());
        } catch (RuntimeException e) {
            // The state stays as it is, so the next window offers it again: an engine that is
            // restarting is a reason to try, and only a spent limit is a reason to stop.
            metrics.record(IngestionRepairMetrics.REFUSED);
            log.warn("the repair could not offer document {} ({}); the next tick tries again", id, e.getMessage());
            return false;
        }
        metrics.record(IngestionRepairMetrics.REQUEUED);
        return true;
    }

    /** The POSTs the clock has actually made for this row; a row with no key has never been offered. */
    private static int offersOf(Document candidate) {
        if (candidate.getMeta() == null || !(candidate.getMeta().get("repair") instanceof Map<?, ?> repair)) {
            return 0;
        }
        return repair.get("attempts") instanceof Number attempts ? attempts.intValue() : 0;
    }
}
