package com.careeros.auth.retention;

import com.careeros.queue.JobHandler;
import java.time.OffsetDateTime;
import java.util.Map;
import org.springframework.stereotype.Component;

/**
 * The nightly retention sweep as a fleet job (Epic 168).
 *
 * <p>The queue made its promise at registration time: one replica runs it, the rest idle.
 * The job this handler runs is idempotent by construction — every delete it issues is a
 * cutoff watermark delete, so a retry after a crash mid-pass is indistinguishable from
 * the pass itself. That is the at-least-once property the handler contract demands, and
 * the reason the sweeper needed no change to ride a fleet queue: the work was already
 * commute-safe against itself.
 *
 * <p>The payload carries nothing; the clock decides the cutoff. An entry enqueued hours
 * before the tick is claimed sends the same window as one claimed now.
 */
@Component
public class RetentionSweepHandler implements JobHandler {

    /** The wire name the lease producer enqueues under, and the only handle this handler has. */
    public static final String KIND = "retention.sweep";

    private final RetentionSweeper sweeper;

    public RetentionSweepHandler(RetentionSweeper sweeper) {
        this.sweeper = sweeper;
    }

    @Override
    public String kind() {
        return KIND;
    }

    @Override
    public void handle(Map<String, String> payload) {
        sweeper.sweep(OffsetDateTime.now());
    }
}
