package com.careeros.job.service;

import com.careeros.queue.JobQueue;
import com.careeros.queue.RedisDayLease;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * The clock the ingestion sweep runs on (roadmap 19.2) — the producer half of the
 * fleet queue enablement (Epic 170).
 *
 * <p>Queue disabled → every replica sweeps inline, exactly the behaviour the install
 * shipped before the queue existed. Queue enabled → one Redis SET NX lease per UTC
 * day (`careeros:v1:lease:ingestion:<yyyy-MM-dd>`) elects the single enqueuing
 * replica; siblings return; the handler claims the job and runs it once. Refusal or a
 * lease error → this replica runs inline: fail open toward the work, never toward a
 * skipped night.
 *
 * <p>The cron is configurable ({@code careeros.ingestion.cron}) so a deployment can move
 * the night without a rebuild; 03:20 is the default, after the corpus's quiet hours.
 * The handler owns the work's own failure posture unchanged: a feed's failure is that
 * feed's run, a fatal error is a warn line, a night that cannot read the enabled list
 * is a logged night rather than a crashed scheduler thread.
 */
@Component
class IngestionScheduler {

    private static final Logger log = LoggerFactory.getLogger(IngestionScheduler.class);

    /** The lease concern this migration races; the UTC day is appended by the lease. */
    static final String CONCERN = "ingestion";

    private final JobQueue queue;
    private final IngestionSweepHandler handler;
    private final RedisDayLease lease;

    IngestionScheduler(JobQueue queue, IngestionSweepHandler handler, RedisDayLease lease) {
        this.queue = queue;
        this.handler = handler;
        this.lease = lease;
    }

    @Scheduled(cron = "${careeros.ingestion.cron:0 20 3 * * *}")
    void sweep() {
        if (!queue.enabled()) {
            handler.handle(Map.of());
            return;
        }
        boolean elected;
        try {
            elected = lease.tryAcquire(CONCERN, LocalDate.now(ZoneOffset.UTC));
        } catch (RuntimeException e) {
            log.warn("the ingestion lease failed ({}); running inline on this replica", e.toString());
            handler.handle(Map.of());
            return;
        }
        if (!elected) {
            return; // a sibling owns tonight's sweep; this replica has nothing to do
        }
        if (queue.enqueue(IngestionSweepHandler.KIND, Map.of())) {
            log.info("nightly ingestion enqueued for the fleet to run once");
            return;
        }
        log.warn("the ingestion lease winner could not enqueue; running inline on this replica");
        handler.handle(Map.of());
    }
}
