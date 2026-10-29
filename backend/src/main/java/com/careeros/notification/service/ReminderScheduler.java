package com.careeros.notification.service;

import com.careeros.push.service.PushDeliveryMetrics;
import java.time.Clock;
import java.time.Duration;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * The minute clock a reminder rings on (roadmap 35.1).
 *
 * <p>The morning pass can only ring what is waiting when it runs; a reminder the reader set for
 * 14:00 would otherwise sit on the board until the next morning. This clock wakes once a minute
 * and asks the board which accounts' reminders fell in the window since the previous completed
 * tick; those accounts' browsers are rung through the same latch the morning uses, so an episode
 * the morning already carried is not rung again, and the same reminder never rings twice.
 *
 * <p>A tick that failed does not advance the window. The next tick therefore asks for the same
 * minute again: the audience query is the only part that can throw here, and a pass that never
 * read its audience must not be remembered as having covered it. The heartbeat moves only when a
 * tick completed, so a clock that stopped reads as a stale {@code careeros.reminders.last.tick}
 * gauge rather than as a board with nothing due.
 *
 * <p>The first window looks back one minute, so the minute a deploy booted in is not lost. A
 * reminder that came due while the process was down for longer than that is not rung by this
 * clock -- its moment is in no window -- but the morning pass still rings it and the inbox has
 * shown it all along; the runbook says so.
 */
@Component
public class ReminderScheduler {

    private static final Logger log = LoggerFactory.getLogger(ReminderScheduler.class);

    /** How far back the first tick after a boot reaches; one tick's worth by default. */
    static final Duration FIRST_WINDOW = Duration.ofMinutes(1);

    private final NotificationPushService push;
    private final PushDeliveryMetrics metrics;
    private final Clock clock;
    private OffsetDateTime lastTick;

    public ReminderScheduler(NotificationPushService push, PushDeliveryMetrics metrics) {
        this(push, metrics, Clock.systemUTC());
    }

    ReminderScheduler(NotificationPushService push, PushDeliveryMetrics metrics, Clock clock) {
        this.push = push;
        this.metrics = metrics;
        this.clock = clock;
        this.lastTick = now().minus(FIRST_WINDOW);
    }

    private OffsetDateTime now() {
        return OffsetDateTime.now(clock).withOffsetSameInstant(ZoneOffset.UTC);
    }

    @Scheduled(fixedDelayString = "${careeros.reminders.tick-ms:60000}")
    public void tick() {
        OffsetDateTime until = now();
        try {
            int rung = push.pushDue(lastTick, until);
            if (rung > 0) {
                log.info("reminder ring delivered to {} account(s)", rung);
            }
            lastTick = until;
        } catch (RuntimeException e) {
            log.warn("the reminder clock could not read its audience; the window is retried", e);
            return;
        }
        metrics.recordDueTick(until);
    }
}
