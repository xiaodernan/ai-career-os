package com.careeros.report.service;

import com.careeros.queue.JobQueue;
import com.careeros.queue.RedisDayLease;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.Map;
import java.util.function.Consumer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * The two clocks the weekly letter runs on (roadmap 19.4, 21.3) — the producer half of
 * the fleet queue enablement (Epic 169).
 *
 * <p>The compose clock fires Monday 08:00: write the week that just ended, mail it,
 * move the heartbeat. The retry clock fires every morning at 09:05: attempt the refused
 * letters under the cap, oldest first. Every replica used to fire both — the compose
 * race costs N× the digest computation, and the retry race mails the same refused
 * letter to the same mailbox N times, so the fleet needs one answer per day, not N.
 *
 * <p>Queue disabled → both handlers run inline on every replica, exactly the behaviour
 * the install shipped before the queue existed; nothing is gated, nothing is deferred.
 * Queue enabled → one UTC-day lease per concern (`digest.compose` / `digest.retry`)
 * elects the single replica that enqueues; siblings return immediately; a refused
 * enqueue sends the leader inline alone; a lease error sends this replica inline —
 * fail-open toward the work, never toward a skipped letter.
 *
 * <p>The business logic lives in {@link WeeklyDigestComposeHandler} and
 * {@link WeeklyDigestRetryHandler} — the same bodies run inline when the queue is off
 * and as claimed jobs when it is on. One implementation of the clock's work.
 */
@Component
class WeeklyDigestScheduler {

    private static final Logger log = LoggerFactory.getLogger(WeeklyDigestScheduler.class);

    private final JobQueue queue;
    private final WeeklyDigestComposeHandler compose;
    private final WeeklyDigestRetryHandler retry;
    private final RedisDayLease lease;

    WeeklyDigestScheduler(JobQueue queue, WeeklyDigestComposeHandler compose,
                          WeeklyDigestRetryHandler retry, RedisDayLease lease) {
        this.queue = queue;
        this.compose = compose;
        this.retry = retry;
        this.lease = lease;
    }

    @Scheduled(cron = "${careeros.digest.cron:0 0 8 * * MON}")
    void publish() {
        dispatch(WeeklyDigestComposeHandler.KIND, "digest.compose", payload -> compose.handle(payload));
    }

    @Scheduled(cron = "0 5 9 * * *")
    void retry() {
        dispatch(WeeklyDigestRetryHandler.KIND, "digest.retry", payload -> retry.handle(payload));
    }

    private void dispatch(String kind, String concern, Consumer<Map<String, String>> inline) {
        if (!queue.enabled()) {
            inline.accept(Map.of());
            return;
        }
        boolean elected;
        try {
            elected = lease.tryAcquire(concern, LocalDate.now(ZoneOffset.UTC));
        } catch (RuntimeException e) {
            log.warn("the weekly digest lease failed for {} ({}); running inline on this replica", kind, e.toString());
            inline.accept(Map.of());
            return;
        }
        if (!elected) {
            return; // a sibling owns this concern today
        }
        if (queue.enqueue(kind, Map.of())) {
            log.info("weekly digest {} enqueued for the fleet to run once", kind);
            return;
        }
        log.warn("the weekly digest {} leader could not enqueue; running inline on this replica", kind);
        inline.accept(Map.of());
    }
}
