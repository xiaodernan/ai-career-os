package com.careeros.job.service;

import com.careeros.queue.JobHandler;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

/**
 * The ingestion sweep as a fleet job (Epic 170).
 *
 * <p>One cron, one call, same body as before — the fleet does it once instead of N
 * times, which matters more than CPU: every enabled feed is a third-party request, and
 * a fleet racing this clock is a fleet asking each subscribed board the same question
 * N times per night. Politeness and rate limits leave the house with this migration.
 *
 * <p>They share the same idempotency the sweep already has (feed upserts keyed by
 * feed identity), so a handler run that fails mid-week re-enters exactly the state the
 * fleet had before it started. The handler swallows a failing night the way the clock
 * did: each feed's failure is already that feed's run, and a fatal error is a warn, not
 * a crash.
 */
@Component
public class IngestionSweepHandler implements JobHandler {

    /** The wire name the producer enqueues under; the only handle this handler has. */
    public static final String KIND = "ingestion.sweep";

    private static final Logger log = LoggerFactory.getLogger(IngestionSweepHandler.class);

    private final ScheduledIngestionService ingestion;

    public IngestionSweepHandler(ScheduledIngestionService ingestion) {
        this.ingestion = ingestion;
    }

    @Override
    public String kind() {
        return KIND;
    }

    @Override
    public void handle(Map<String, String> payload) {
        try {
            int due = ingestion.sweepEnabled();
            log.info("nightly ingestion swept {} feed(s)", due);
        } catch (RuntimeException e) {
            log.warn("nightly ingestion could not run", e);
        }
    }
}
