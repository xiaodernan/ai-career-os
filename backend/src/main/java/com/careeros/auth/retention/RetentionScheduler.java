package com.careeros.auth.retention;

import com.careeros.queue.JobQueue;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * The retention sweep's one tick per replica (Epic 168) — the producer half of the
 * queue enablement.
 *
 * <p>The @Scheduled flow keeps today's meaning until the queue is enabled: when
 * {@code careeros.queue.enabled} is false or Redis refused the entry, this replica
 * sweeps inline — byte-for-byte the pre-queue behaviour, every replica doing the full
 * pass, as it did before the queue existed.
 *
 * <p>When the queue is enabled, the pass must happen <em>once per fleet</em>, and the
 * queue's at-least-once guarantee alone cannot promise that: N replicas all fire at
 * 04:47 and would enqueue N identical entries, N replicas each grabbing one and each doing
 * the full bucket list — the same collection work N times over, the most expensive phase
 * of the job. So the tick elects one leader per UTC day with a single Redis SET NX
 * ({@code EX 1 day}); only the elected replica enqueues. Siblings do nothing — their
 * work is covered by the leader's enqueue, and the queue's worker will claim it.
 *
 * <p>When the election errors out (Redis hiccup exactly at the tick), the replica runs
 * the sweep inline: one duplicated pass is better than no pass, and this code path is
 * free to swallow the failure because the lost promise is a batch of deletes the next
 * night will finish. Honest bounds: a leader that dies after the election and before the
 * enqueue leaves the night unattended by the queue — the sweep's heartbeat alarm
 * (`careeros_retention_last_sweep_timestamp`) fires after its 36-hour silence, which is
 * the designed messenger for a stopped clock, not this code's job to presume from.
 */
@Component
class RetentionScheduler {

    private static final Logger log = LoggerFactory.getLogger(RetentionScheduler.class);

    /** The eligibility key: N replicas race once per day; one wins the right to enqueue. */
    public static final String LEADER_KEY_PREFIX = "careeros:v1:retention:owner:";

    private final JobQueue queue;
    private final RetentionSweeper sweeper;
    private final StringRedisTemplate redis;

    RetentionScheduler(JobQueue queue, RetentionSweeper sweeper, StringRedisTemplate redis) {
        this.queue = queue;
        this.sweeper = sweeper;
        this.redis = redis;
    }

    @Scheduled(cron = "${careeros.retention.cron:0 47 4 * * *}")
    void tick() {
        if (!queue.enabled()) {
            sweepInline("queue disabled");
            return;
        }
        if (!electedLeader()) {
            return; // the leader enqueued (or runs inline itself); this replica has nothing to do
        }
        if (queue.enqueue(RetentionSweepHandler.KIND, Map.of())) {
            log.info("retention sweep enqueued for the fleet to run once");
            return;
        }
        log.warn("retention leader refused/enqueued nothing; running inline on this replica");
        sweepInline("leader could not enqueue");
    }

    /** Package-private so tests can read the key shape. */
    static String leaderKey(LocalDate day) {
        return LEADER_KEY_PREFIX + day;
    }

    private boolean electedLeader() {
        try {
            Boolean won = redis.opsForValue().setIfAbsent(
                    leaderKey(LocalDate.now(ZoneOffset.UTC)), "1", java.time.Duration.ofDays(1));
            return Boolean.TRUE.equals(won);
        } catch (RuntimeException e) {
            log.warn("retention leader election failed ({}); running inline on this replica", e.toString());
            return true; // fail-open toward the work: a duplicate pass beats a skipped one
        }
    }

    private void sweepInline(String reason) {
        log.info("retention sweep running inline ({})", reason);
        sweeper.sweep(OffsetDateTime.now());
    }
}
