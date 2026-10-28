package com.careeros.report.service;

import java.time.LocalDate;
import java.time.ZoneOffset;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * The clock the weekly letter runs on (roadmap 19.4).
 *
 * <p>Monday morning, the week that just ended is written down: at 08:00 the week's rows can no
 * longer change, so the letter is final the moment it is composed. Nothing is thrown out of
 * here -- each user's failure is already a warn line inside the sweep, and a night that could
 * not even read the audience is logged rather than crashing the scheduler's thread. The cron is
 * configurable ({@code careeros.digest.cron}) so a deployment can move it without a rebuild.
 */
@Component
public class WeeklyDigestScheduler {

    private static final Logger log = LoggerFactory.getLogger(WeeklyDigestScheduler.class);

    private final WeeklyDigestService digests;

    public WeeklyDigestScheduler(WeeklyDigestService digests) {
        this.digests = digests;
    }

    @Scheduled(cron = "${careeros.digest.cron:0 0 8 * * MON}")
    public void publish() {
        try {
            LocalDate week = WeeklyDigestService
                    .weekStartOf(LocalDate.now(ZoneOffset.UTC)).minusWeeks(1);
            int written = digests.composeWeek(week);
            log.info("weekly digest composed {} letter(s) for the week of {}", written, week);
        } catch (RuntimeException e) {
            log.warn("the weekly digest could not run", e);
        }
    }
}
