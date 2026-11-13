package com.careeros.report.service;

import com.careeros.queue.JobHandler;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

/**
 * The Monday compose sweep as a fleet job (Epic 169).
 *
 * <p>The night writes the week that just ended, mails it, and moves the heartbeat so an
 * install whose Monday never fired is visible; a failure is logged and reported as a
 * failed compose, never thrown — a scheduler thread that dies costs every future night.
 * Everything the clock did is still what the clock does here, unchanged; the handler
 * exists so one fleet replica may do it instead of all of them racing the same letter
 * fanout N times over (each compose costs the same deterministic digest computation and
 * an upsert of the same row — correct, but multiplied).
 *
 * <p>Idempotency of the sweep (re-composition refreshes the same row, delivery is
 * latched by {@code delivered_at}) is what makes this a safe at-least-once job: the
 * handler contract requires at-least-once-safe bodies and this is already one.
 */
@Component
public class WeeklyDigestComposeHandler implements JobHandler {

    /** The wire name the producer enqueues under; the only handle this handler has. */
    public static final String KIND = "digest.compose";

    private static final Logger log = LoggerFactory.getLogger(WeeklyDigestComposeHandler.class);

    private final WeeklyDigestService digests;
    private final WeeklyDigestDeliveryMetrics metrics;

    public WeeklyDigestComposeHandler(WeeklyDigestService digests, WeeklyDigestDeliveryMetrics metrics) {
        this.digests = digests;
        this.metrics = metrics;
    }

    @Override
    public String kind() {
        return KIND;
    }

    @Override
    public void handle(Map<String, String> payload) {
        try {
            LocalDate week = WeeklyDigestService
                    .weekStartOf(LocalDate.now(ZoneOffset.UTC)).minusWeeks(1);
            int written = digests.composeWeek(week);
            metrics.recordSweep(OffsetDateTime.now(ZoneOffset.UTC));
            log.info("weekly digest composed {} letter(s) for the week of {}", written, week);
        } catch (RuntimeException e) {
            log.warn("the weekly digest could not run", e);
        }
    }
}
