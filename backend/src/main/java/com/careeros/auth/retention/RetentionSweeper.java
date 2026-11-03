package com.careeros.auth.retention;

import com.careeros.auth.repository.EmailChangeTokenRepository;
import com.careeros.auth.repository.PasswordResetTokenRepository;
import com.careeros.auth.repository.RefreshTokenRepository;
import com.careeros.config.AppProperties;
import com.careeros.knowledge.service.RetiredEvidencePurger;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * Deletes what the install no longer needs: credential rows expired past the grace window
 * (roadmap 28.1) and the audit records of deletes that have aged out of theirs (44.3).
 *
 * <p>A token row outlives the token. Nothing reads an expired refresh, reset or address-change
 * token -- every lookup is by hash and every consumer checks expiry -- but the row stays until
 * someone deletes it, and each sign-in, reset request and address move writes one. Left alone,
 * the three credential tables grow with the install's entire history of them.
 *
 * <p>The cutoff is the sweep's clock minus a grace window, not "expired now": a row is deleted
 * only once its expiry is that far behind the clock, so a clock-skewed client, a support
 * investigation or a late-arriving request still finds its row. The default is thirty days past
 * expiry, and the window is an operator knob ({@code app.retention.expired-token-days}).
 *
 * <p>The evidence phase runs on the same shape with a different clock: a document the delete
 * path retired keeps its row and its chunks as the record of what was quoted, and
 * {@code app.retention.retired-document-days} (180 by default) is how long that record is kept
 * before the row, its chunks and -- through 44.2's reclaim -- the object behind its key go. The
 * purge is a phase of this schedule rather than a second one because the two questions are
 * answered by the same clock, and an operator who finds the sweep stopped should not have to
 * notice that only half of it stopped.
 *
 * <p>The bucket phase asks the third question the same clock answers. Everything the two phases
 * above prune is named by a row: an expired token has its table, a retired document its audit
 * record. The objects the store holds that no row names are invisible to both of those deletes --
 * bytes stored by a request whose row never arrived, or freed by a purge whose reclaim the store
 * refused -- and they are what {@link UnnamedObjectReclaimer} subtracts the two key columns from,
 * once {@code app.retention.unnamed-object-days} (7 by default) has passed over them. That window
 * is the whole difference between a janitor and a data-loss bug: an object is only garbage once the
 * request that stored it can no longer be on its way to a row, and a pass that reclaimed anything
 * younger would be deleting the upload of a reader still waiting for their document to appear.
 *
 * <p>Each table is swept in its own transaction, so a lock timeout on one leaves the other two
 * pruned rather than rolling the whole night back; a failed table is logged and omitted from
 * the summary, and no metric moves for it, so the counter tells an operator which tables were
 * actually swept. The pass then moves the heartbeat gauge even if a table failed: the gauge
 * answers whether the schedule still runs, and a pass that ran and failed is a different fault
 * from a clock that stopped. The tables that hold visible history -- AI usage events behind the
 * activity totals, notification read state, ingestion runs, weekly letters -- are deliberately
 * absent: removing their rows would rewrite a screen or re-announce a story the reader already
 * settled.
 */
@Component
public class RetentionSweeper {

    static final String REFRESH_TOKENS = "refresh_tokens";
    static final String PASSWORD_RESET_TOKENS = "password_reset_tokens";
    static final String EMAIL_CHANGE_TOKENS = "email_change_tokens";
    static final String DOCUMENTS = "documents";
    static final String DOCUMENT_CHUNKS = "document_chunks";

    /** The evidence tables the content phase removes in one transaction, so one failure names both. */
    private static final List<String> EVIDENCE_TABLES = List.of(DOCUMENTS, DOCUMENT_CHUNKS);

    /** The bucket is not a table, but a phase that could not finish it is reported like one. */
    static final String BUCKET_OBJECTS = "bucket_objects";

    private static final Logger log = LoggerFactory.getLogger(RetentionSweeper.class);

    private final RefreshTokenRepository refreshTokens;
    private final PasswordResetTokenRepository resetTokens;
    private final EmailChangeTokenRepository emailChangeTokens;
    private final RetiredEvidencePurger evidence;
    private final UnnamedObjectReclaimer unnamed;
    private final AppProperties props;
    private final RetentionMetrics metrics;

    public RetentionSweeper(RefreshTokenRepository refreshTokens,
                            PasswordResetTokenRepository resetTokens,
                            EmailChangeTokenRepository emailChangeTokens,
                            RetiredEvidencePurger evidence,
                            UnnamedObjectReclaimer unnamed,
                            AppProperties props, RetentionMetrics metrics) {
        this.refreshTokens = refreshTokens;
        this.resetTokens = resetTokens;
        this.emailChangeTokens = emailChangeTokens;
        this.evidence = evidence;
        this.unnamed = unnamed;
        this.props = props;
        this.metrics = metrics;
    }

    @Scheduled(cron = "${careeros.retention.cron:0 47 4 * * *}")
    public void nightly() {
        sweep(OffsetDateTime.now());
    }

    /**
     * One sweep at {@code now}. Package-private so the tests can hand it a fixed clock instead
     * of waiting for 04:47.
     */
    Sweep sweep(OffsetDateTime now) {
        Map<String, Long> deleted = new LinkedHashMap<>();
        List<String> failed = new ArrayList<>();
        sweepCredentials(now, deleted, failed);
        sweepRetiredEvidence(now, deleted, failed);
        sweepUnnamedObjects(now, failed);
        metrics.recordSweep(now);
        log.info("Retention sweep removed {} row(s) at {} ({})",
                deleted.values().stream().mapToLong(Long::longValue).sum(), now, deleted);
        return new Sweep(deleted, failed);
    }

    /** Each table in its own transaction, so a lock timeout on one leaves the other two pruned. */
    private void sweepCredentials(OffsetDateTime now, Map<String, Long> deleted, List<String> failed) {
        int days = Math.max(0, props.getRetention().getExpiredTokenDays());
        OffsetDateTime cutoff = now.minusDays(days);
        for (String table : List.of(REFRESH_TOKENS, PASSWORD_RESET_TOKENS, EMAIL_CHANGE_TOKENS)) {
            try {
                long rows = switch (table) {
                    case REFRESH_TOKENS -> refreshTokens.deleteExpiredBefore(cutoff);
                    case PASSWORD_RESET_TOKENS -> resetTokens.deleteExpiredBefore(cutoff);
                    default -> emailChangeTokens.deleteExpiredBefore(cutoff);
                };
                deleted.put(table, rows);
                metrics.record(table, rows);
            } catch (RuntimeException e) {
                failed.add(table);
                log.warn("Retention sweep failed for {}; the other tables keep their own rows", table, e);
            }
        }
    }

    /**
     * The window is measured from the retirement, which is the row's last write: a late ingest
     * is refused and nothing else touches a retired document. A purge that fails leaves both
     * evidence tables without a reading, because the rows and their cascaded chunks go in the
     * same statement -- and it cannot have taken a file either, since the reclaim it queues runs
     * only after that statement's transaction commits.
     */
    private void sweepRetiredEvidence(OffsetDateTime now, Map<String, Long> deleted,
                                      List<String> failed) {
        int days = Math.max(0, props.getRetention().getRetiredDocumentDays());
        OffsetDateTime cutoff = now.minusDays(days);
        try {
            RetiredEvidencePurger.Purge purge = evidence.purgeBefore(cutoff);
            deleted.put(DOCUMENTS, (long) purge.documents());
            deleted.put(DOCUMENT_CHUNKS, purge.chunks());
            metrics.record(DOCUMENTS, purge.documents());
            metrics.record(DOCUMENT_CHUNKS, purge.chunks());
            if (purge.leftNamed() > 0) {
                log.warn("Retention sweep left {} retired document row(s) older than {} because a "
                        + "source row still names them", purge.leftNamed(), cutoff);
            }
        } catch (RuntimeException e) {
            failed.addAll(EVIDENCE_TABLES);
            log.warn("Retention sweep failed for {}; the credential tables keep their own rows",
                    EVIDENCE_TABLES, e);
        }
    }

    /**
     * The bucket's own phase, last because the purge above is what frees most of what it finds:
     * that pass commits before this one starts, so a retired row has already stopped naming its
     * key and a reclaim the store accepted has already taken the object out of the listing. What
     * is left for the bucket to name is a row that no longer exists -- which is precisely the
     * object no other delete can reach.
     *
     * <p>Its readings are the reclaimer's four verdicts, counted per object rather than per row,
     * so they stay on their own meter and out of the summary's row counts. A pass that could not
     * list the bucket moves none of them and is named in the failed list: nothing was reclaimed,
     * because the sweep that cannot see the bucket cannot see that it is empty either.
     */
    private void sweepUnnamedObjects(OffsetDateTime now, List<String> failed) {
        int days = Math.max(0, props.getRetention().getUnnamedObjectDays());
        try {
            UnnamedObjectReclaimer.Reclaim reclaim = unnamed.reclaimBefore(now.minusDays(days));
            log.info("Retention sweep judged {} bucket object(s) at {} "
                            + "({} named by a row, {} inside the window, {} reclaimed, {} refused)",
                    reclaim.listed(), now, reclaim.named(), reclaim.young(),
                    reclaim.deleted(), reclaim.failed());
        } catch (RuntimeException e) {
            failed.add(BUCKET_OBJECTS);
            log.warn("Retention sweep could not list the bucket, so it reclaimed nothing; "
                    + "a store that refused is not a store that answered empty", e);
        }
    }

    /** What one sweep removed per table, and the things -- tables and bucket -- it could not finish. */
    record Sweep(Map<String, Long> deleted, List<String> failed) {
    }
}
