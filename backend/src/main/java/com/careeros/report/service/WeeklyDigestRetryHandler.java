package com.careeros.report.service;

import com.careeros.queue.JobHandler;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

/**
 * The morning retry as a fleet job (Epic 169).
 *
 * <p>Only letters the transport refused are retried, oldest week first, and each is
 * attempted up to the cap before being left on its row with the last error. The race
 * this exists to close: N replicas fire at 09:05 UTC, each asking for the same
 * undelivered candidates, and each mailing whatever it finds — a reader getting the
 * same letter twice because the fleet could not agree on who asked first.
 *
 * <p>Two replicas enqueuing the same stale candidate set is exactly what the lease
 * mirrors: worthless when both mail the same refused letter in the same millisecond,
 * perfect when one replica does it while the rest rest. The handler would still honor
 * its contract if two claimed two copies of the same candidate — each does its own
 * attempt safely; the fleet simply prefers not to pay the mail relay twice for the
 * same week.
 */
@Component
public class WeeklyDigestRetryHandler implements JobHandler {

    /** The wire name the producer enqueues under. */
    public static final String KIND = "digest.retry";

    private static final Logger log = LoggerFactory.getLogger(WeeklyDigestRetryHandler.class);

    private final WeeklyDigestService digests;

    public WeeklyDigestRetryHandler(WeeklyDigestService digests) {
        this.digests = digests;
    }

    @Override
    public String kind() {
        return KIND;
    }

    @Override
    public void handle(Map<String, String> payload) {
        try {
            int delivered = digests.retryUndelivered();
            if (delivered > 0) {
                log.info("weekly digest retry delivered {} letter(s)", delivered);
            }
        } catch (RuntimeException e) {
            log.warn("the weekly digest retry could not run", e);
        }
    }
}
