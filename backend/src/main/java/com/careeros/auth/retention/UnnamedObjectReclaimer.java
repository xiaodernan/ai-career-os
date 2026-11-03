package com.careeros.auth.retention;

import com.careeros.knowledge.repository.DocumentRepository;
import com.careeros.resume.repository.ResumeRepository;
import com.careeros.storage.StorageService;
import com.careeros.storage.StorageService.StoredObject;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import java.time.OffsetDateTime;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

/**
 * Reclaims the objects the bucket holds that no row names, once they are past a window
 * (roadmap 48.2).
 *
 * <p>Storing bytes and naming them are not one act. {@code put} lands in the object store and the
 * row that carries its key lands in the database, in a transaction the store does not join, so a
 * rollback or a crash between the two leaves an object that nothing will ever name -- and every
 * path written before this one only looks at objects a row points at. Two more arrive the same way
 * on purpose: 44.2's reclaim asks the store for a key and the store refuses, and 44.3's purge then
 * deletes the row that was holding the claim. Nothing until now ever read the bucket.
 *
 * <p>The order of the two reads is the whole safety of this pass, so it is worth stating plainly:
 * the listing is taken first and the rows are read after it. A key that appears in the listing was
 * stored before the listing ran; a row committed after that moment is in the set the subtraction
 * uses, and a row that will commit later is still protected by the window, because the object it
 * names cannot be older than the transaction that stored it. Take the rows first and the order
 * reverses into a deletion: an upload that stored its bytes, paused, and committed its row after
 * this pass read the tables would find its file reclaimed out from under a row that exists.
 *
 * <p>The window is measured on {@link StoredObject#lastModified()} -- the store's own account of
 * when the bytes landed -- and an object is only ever reclaimed for being strictly older than the
 * cutoff. That direction matters twice: an object the store cannot date is dated by the listing
 * that read it (48.1), so it arrives as young and stays; and a store whose clock runs ahead of
 * this one produces an object that looks younger than it is, which costs a week of storage rather
 * than a reader's file.
 *
 * <p>"Any row names it" is read wider here than 44.2 reads it. The delete path asks whether a
 * still-quotable row claims a key, because an audit record is not a reason to hold bytes; this
 * path asks whether any row at all claims one, because a row that exists is a row that could still
 * be asked for its file, and a retired row is exactly the trail 44.2 leaves a refused reclaim on.
 * The row's own delete is what releases the object, and it does that through the reclaimer --
 * which is why this phase runs last, after the purge has committed and its reclaim has already
 * tried: an object the purge freed is a candidate tonight, and an object the purge freed and the
 * store refused is a candidate for as many nights as it takes.
 *
 * <p>A listing that refuses is not a bucket that is empty. {@link StorageService#list()} throws
 * rather than answering short, and this pass lets the throw out, because the caller that catches it
 * -- {@link RetentionSweeper}'s phase -- is the one that knows how to say "the bucket was not
 * swept" without saying "the bucket was clean". Converting that into an empty list would charge
 * every object in the install against a read that never happened. The refusal is counted before it
 * travels, on its own meter and once per pass rather than once per object: the sweep's clock keeps
 * moving through a refused listing, so the reading is the only thing that tells an operator the
 * bucket half of the night did not run.
 *
 * <p>One object's failure is one object's failure: a store that refuses a delete is counted and
 * logged and the pass goes on to the next key, because ninety keys are not worth leaving behind
 * for the one the store would not take. The four verdicts are counted on one meter and sum to the
 * listing, so the reading checks its own arithmetic -- an operator who sees the four add up short
 * knows the pass ended early, and a clock that stopped mid-pass says so in the same place.
 */
@Service
public class UnnamedObjectReclaimer {

    static final String JUDGED = "careeros.storage.objects_judged";
    private static final String DESCRIPTION =
            "Objects the bucket listing showed the nightly sweep, by what it decided to do about them";

    static final String READS = "careeros.storage.bucket_reads";
    private static final String READS_DESCRIPTION =
            "Nights the retention sweep asked the bucket for its whole listing, by whether the store answered";

    static final String NAMED = "named";
    static final String YOUNG = "young";
    static final String DELETED = "deleted";
    static final String FAILED = "failed";

    static final String LISTED = "listed";
    static final String REFUSED = "refused";

    private static final Logger log = LoggerFactory.getLogger(UnnamedObjectReclaimer.class);

    private final DocumentRepository documents;
    private final ResumeRepository resumes;
    private final StorageService storage;
    private final MeterRegistry registry;
    private final Map<String, Counter> counters = new ConcurrentHashMap<>();

    public UnnamedObjectReclaimer(DocumentRepository documents, ResumeRepository resumes,
                                  StorageService storage, MeterRegistry registry) {
        this.documents = documents;
        this.resumes = resumes;
        this.storage = storage;
        this.registry = registry;
    }

    /**
     * Judge every object the store shows against every key the two owner tables hold.
     *
     * @param cutoff an object last written before this moment is old enough to reclaim
     */
    public Reclaim reclaimBefore(OffsetDateTime cutoff) {
        List<StoredObject> listed;
        try {
            listed = storage.list();
        } catch (RuntimeException refusal) {
            recordRead(REFUSED);
            throw refusal;
        }
        recordRead(LISTED);
        Set<String> named = new HashSet<>();
        named.addAll(documents.findAllFileKeys());
        named.addAll(resumes.findAllSourceFileKeys());

        long kept = 0;
        long young = 0;
        int reclaimed = 0;
        int refused = 0;
        for (StoredObject object : listed) {
            if (named.contains(object.key())) {
                kept++;
                record(NAMED);
                continue;
            }
            if (!object.lastModified().isBefore(cutoff)) {
                young++;
                record(YOUNG);
                continue;
            }
            try {
                storage.delete(object.key());
                reclaimed++;
                record(DELETED);
            } catch (RuntimeException e) {
                refused++;
                record(FAILED);
                log.warn("Reclaiming the unclaimed object {} failed: {}", object.key(), e.getMessage());
            }
        }
        return new Reclaim(listed.size(), kept, young, reclaimed, refused);
    }

    private void record(String outcome) {
        counter(JUDGED, DESCRIPTION, outcome).increment();
    }

    private void recordRead(String outcome) {
        counter(READS, READS_DESCRIPTION, outcome).increment();
    }

    private Counter counter(String meter, String description, String outcome) {
        return counters.computeIfAbsent(meter + "/" + outcome, ignored -> Counter.builder(meter)
                        .tag("outcome", outcome)
                        .description(description)
                        .register(registry));
    }

    /**
     * What one pass saw and decided: the size of the listing, and the four verdicts that add up to
     * it -- a key a row still names, an object too young for the window, bytes the store gave up,
     * and bytes the store refused to give up.
     */
    public record Reclaim(long listed, long named, long young, int deleted, int failed) {
    }
}
