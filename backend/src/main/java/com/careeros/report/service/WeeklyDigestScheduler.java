package com.careeros.report.service;

import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * The clocks the weekly letter runs on (roadmap 19.4, 21.3).
 *
 * <p>Monday morning, the week that just ended is written down: at 08:00 the week's rows can no
 * longer change, so the letter is final the moment it is composed. The second clock is the
 * retry: every morning at 09:05 UTC the letters the transport refused are tried again, oldest
 * week first, until the service's cap. Nothing is thrown out of either -- each user's failure
 * is already a warn line inside the sweep, and a night that could not even read the audience is
 * logged rather than crashing the scheduler's thread. The compose cron is configurable
 * ({@code careeros.digest.cron}) so a deployment can move it without a rebuild; the retry is
 * fixed at an hour that leaves the relay time to have been fixed the evening before. A
 * completed Monday compose moves the heartbeat (roadmap 22.4) even when the week had no
 * accounts, so a clock that never fired is visible; a failed compose does not, and neither
 * does a retry, which is a different promise.
 */
@Component
public class WeeklyDigestScheduler {

    private static final Logger log = LoggerFactory.getLogger(WeeklyDigestScheduler.class);

    private final WeeklyDigestService digests;
    private final WeeklyDigestDeliveryMetrics metrics;

    public WeeklyDigestScheduler(WeeklyDigestService digests, WeeklyDigestDeliveryMetrics metrics) {
        this.digests = digests;
        this.metrics = metrics;
    }

    @Scheduled(cron = "${careeros.digest.cron:0 0 8 * * MON}")
    public void publish() {
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

    /** The morning retry: only letters that were attempted and are under the cap. */
    @Scheduled(cron = "0 5 9 * * *")
    public void retry() {
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
