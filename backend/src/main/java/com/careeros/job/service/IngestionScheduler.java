package com.careeros.job.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * The clock the ingestion sweep runs on (roadmap 19.2).
 *
 * <p>Nothing is returned and nothing is thrown out of here: the sweep already turns
 * each feed's failure into that feed's own run, and a night that could not even read
 * the enabled list is logged rather than crashing the scheduler's thread. The cron is
 * configurable ({@code careeros.ingestion.cron}) so a deployment can move the night
 * without a rebuild; 03:20 is the default because it is after the corpus's own quiet
 * hours and before anyone reads the board.
 */
@Component
public class IngestionScheduler {

    private static final Logger log = LoggerFactory.getLogger(IngestionScheduler.class);

    private final ScheduledIngestionService ingestion;

    public IngestionScheduler(ScheduledIngestionService ingestion) {
        this.ingestion = ingestion;
    }

    @Scheduled(cron = "${careeros.ingestion.cron:0 20 3 * * *}")
    public void sweep() {
        try {
            int due = ingestion.sweepEnabled();
            log.info("nightly ingestion swept {} feed(s)", due);
        } catch (RuntimeException e) {
            log.warn("nightly ingestion could not run", e);
        }
    }
}
