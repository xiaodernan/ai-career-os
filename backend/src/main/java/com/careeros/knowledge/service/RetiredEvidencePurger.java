package com.careeros.knowledge.service;

import com.careeros.knowledge.repository.DocumentRepository;
import java.time.OffsetDateTime;
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Purges the audit record a delete leaves behind, once the window on it has passed (roadmap
 * 44.3).
 *
 * <p>Retirement is deliberately not a delete: the row and its chunks stay so that what the
 * assistant once quoted can still be traced, and 44.2 leaves the row naming its object key so
 * account erasure can finish a reclaim the store refused. Both of those promises are about a
 * record with an end, and this is the end. A row retired before {@code cutoff} goes, the
 * database takes its chunks with it through {@code on delete cascade}, and the key it named is
 * handed to {@link StoredObjectReclaimer} -- the sweep has to ask the store while the row that
 * names the object still exists, because after this pass nothing does.
 *
 * <p>One row is left alone: a retired document a source row still points at. The delete path
 * drops the source in the same transaction that retires the copy, so normally there are none;
 * if one appears, its object is still reachable through that source, and taking the row would
 * break the source's own delete to hurry an audit record along. The number is reported rather
 * than hidden, because a purge that quietly removes nothing looks exactly like a night with
 * nothing to purge.
 *
 * <p>Everything here is one transaction, so a purge that fails takes neither rows nor files:
 * the reclaim it queues runs only when the rows are durable, and the next night retries.
 */
@Service
public class RetiredEvidencePurger {

    private static final String STATUS_RETIRED = "retired";

    private final DocumentRepository documents;
    private final StoredObjectReclaimer reclaimer;

    public RetiredEvidencePurger(DocumentRepository documents, StoredObjectReclaimer reclaimer) {
        this.documents = documents;
        this.reclaimer = reclaimer;
    }

    @Transactional
    public Purge purgeBefore(OffsetDateTime cutoff) {
        long chunks = documents.countRetiredChunksBefore(STATUS_RETIRED, cutoff);
        List<String> keys = documents.findRetiredFileKeysBefore(STATUS_RETIRED, cutoff);
        int rows = documents.deleteRetiredBefore(STATUS_RETIRED, cutoff);
        reclaimer.reclaim(keys);
        long stillNamed = documents.countRetiredButStillNamedBefore(STATUS_RETIRED, cutoff);
        return new Purge(rows, chunks, stillNamed);
    }

    /**
     * What one purge pass removed: the document rows it deleted, the chunks the cascade took
     * with them, and the retired rows past the window it left because a source still named
     * them.
     */
    public record Purge(int documents, long chunks, long leftNamed) {
    }
}
