package com.careeros.knowledge.service;

import com.careeros.knowledge.repository.DocumentRepository;
import com.careeros.resume.repository.ResumeRepository;
import com.careeros.storage.StorageService;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import java.util.Collection;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;

/**
 * Reclaims the object an upload stored once no row names it any more (roadmap 44.2).
 *
 * <p>Deleting an item is a row transaction; the object store is not in it. The question this asks --
 * does any row still name this key -- is only answerable once the caller's rows are durable, so a
 * reclaim called while a transaction is open is deferred to that transaction's commit and a
 * rollback never takes a file. A delete of one item commits on its own; a bundle restore deletes
 * many rows in one transaction it owns, and both shapes have to be judged at the same moment.
 * Putting the wait here is what stops each new caller from having to remember it.
 *
 * <p>The two halves of an upload share one key -- a resume's detail page serves the bytes its upload
 * stored, while the ingested copy made from them is a separate row. Deleting the knowledge entry
 * therefore must not take the resume's original file with it, and deleting the resume -- which
 * retires the copy and removes the row in the same transaction -- must.
 *
 * <p>Reclamation is the last step of a delete that already succeeded, so a store that refuses is
 * counted and logged rather than turned into an error about a thing the reader no longer has. The
 * retired row keeps its key, which is what lets account erasure find whatever a failed reclaim left.
 */
@Service
public class StoredObjectReclaimer {

    static final String RECLAIMED = "careeros.storage.objects_reclaimed";
    private static final String DESCRIPTION =
            "Stored uploads judged by the delete path, by whether the object was reclaimed";
    private static final String STATUS_RETIRED = "retired";

    private static final Logger log = LoggerFactory.getLogger(StoredObjectReclaimer.class);

    private final DocumentRepository documents;
    private final ResumeRepository resumes;
    private final StorageService storage;
    private final MeterRegistry registry;
    private final Map<String, Counter> counters = new ConcurrentHashMap<>();

    public StoredObjectReclaimer(DocumentRepository documents, ResumeRepository resumes,
                                StorageService storage, MeterRegistry registry) {
        this.documents = documents;
        this.resumes = resumes;
        this.storage = storage;
        this.registry = registry;
    }

    /**
     * Judge each key an item this delete retired named. A text ingestion names none, so the usual
     * answer is that there is nothing to judge.
     */
    public void reclaim(Collection<String> fileKeys) {
        Set<String> unique = new LinkedHashSet<>();
        for (String key : fileKeys) {
            if (key != null && !key.isBlank()) {
                unique.add(key);
            }
        }
        if (unique.isEmpty()) {
            return;
        }
        List<String> keys = List.copyOf(unique);
        if (!TransactionSynchronizationManager.isSynchronizationActive()) {
            judge(keys);
            return;
        }
        TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
            @Override
            public void afterCommit() {
                judge(keys);
            }
        });
    }

    /** One key, one question, one outcome -- and a store that refuses cannot undo the rows. */
    private void judge(List<String> keys) {
        for (String key : keys) {
            try {
                if (documents.existsByFileKeyAndStatusNot(key, STATUS_RETIRED)
                        || resumes.existsBySourceFileKey(key)) {
                    record("referenced");
                    continue;
                }
                storage.delete(key);
                record("deleted");
            } catch (RuntimeException e) {
                record("failed");
                log.warn("Reclaiming the stored object {} failed: {}", key, e.getMessage());
            }
        }
    }

    private void record(String outcome) {
        counters.computeIfAbsent(outcome, name -> Counter.builder(RECLAIMED)
                        .tag("outcome", name)
                        .description(DESCRIPTION)
                        .register(registry))
                .increment();
    }
}
