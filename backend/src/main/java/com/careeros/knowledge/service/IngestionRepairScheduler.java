package com.careeros.knowledge.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * The clock the repair pass runs on (Epic 418).
 *
 * <p>Ten minutes, because the thing it catches is a reader watching an upload that will never
 * finish, and "never" is only tolerable for about one window of it. The first pass runs as the
 * process starts, which is the moment this clock earns its keep: a rolling deploy is exactly how
 * a document ends up committed and un-offered, and the replicas that survive it should look for
 * those rows rather than wait out a delay. The interval is a knob; the window the pass compares
 * rows against is the other one, and the two have to be read together: shortening the interval
 * without shortening the window does not make a stuck document get picked up any sooner, it only
 * makes more ticks find nothing.
 *
 * <p>Every replica rings this clock, and that is the behaviour the install already has for a job
 * the fleet lease was built to replace — here it costs nothing, because the pass claims each row
 * in the database before it offers it, so a tick that arrives second reads 0 and steps on. What
 * a lease would decide — which replica gets to make the offer — is already decided by the row.
 *
 * <p>A tick that throws does not move the heartbeat, which is the point: {@code
 * careeros_ingestion_repair_last_tick_timestamp} going stale is the difference between a quiet
 * install and a clock that stopped, and the warn line is which side of that this install is on.
 * The scheduler swallows the failure rather than letting it kill the thread, exactly as the
 * ingestion and retention clocks do, so the next window gets its own chance.
 */
@Component
public class IngestionRepairScheduler {

    private static final Logger log = LoggerFactory.getLogger(IngestionRepairScheduler.class);

    private final IngestionRepairService repair;

    IngestionRepairScheduler(IngestionRepairService repair) {
        this.repair = repair;
    }

    /**
     * The pass itself. Silent when there was nothing to repair — a quiet install would otherwise
     * write a log line every ten minutes forever — and one line per tick that found work, because
     * the number of documents the clock rescued is the reading an operator wants from the log.
     */
    @Scheduled(fixedDelayString = "${careeros.ingestion.repair.interval-ms:600000}")
    void repairStuckIngestions() {
        try {
            int offered = repair.sweep();
            if (offered > 0) {
                log.info("the ingestion repair offered {} document(s) back to the engine", offered);
            }
        } catch (RuntimeException e) {
            log.warn("the stuck-ingestion repair could not run", e);
        }
    }
}
