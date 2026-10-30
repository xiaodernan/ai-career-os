package com.careeros.notification.service;

import com.careeros.push.service.PushDeliveryMetrics;
import java.time.Clock;
import java.time.Duration;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * The minute clock a reminder rings on (roadmap 35.1, letter 41.1).
 *
 * <p>The morning pass can only ring what is waiting when it runs; a reminder the reader set for
 * 14:00 would otherwise sit on the board until the next morning. This clock wakes once a minute
 * and asks the board which accounts' reminders fell in the window since the previous completed
 * tick; those accounts' browsers are rung through the same latch the morning uses, so an episode
 * the morning already carried is not rung again, and the same reminder never rings twice. The
 * tick writes the reminder's own letter too (roadmap 41.1), for the reader whose mailbox is the
 * surface they are near rather than the browser.
 *
 * <p>The two halves are caught separately on purpose: a relay that refuses every letter should
 * not silence a browser that could have rung, and a push transport that hangs should not cost
 * the tick its letter. A tick that failed in either half does not advance the window. The next
 * tick therefore asks for the same minute again: the audience queries are the only part that can
 * throw here, and a pass that never read its audience must not be remembered as having covered
 * it. Each half's latch keeps the retry from sending twice, so asking again costs a read rather
 * than a duplicate. The heartbeat moves only when a tick completed, so a clock that stopped
 * reads as a stale {@code careeros.reminders.last.tick} gauge rather than as a board with
 * nothing due.
 *
 * <p>The first window looks back one minute, so the minute a deploy booted in is not lost. A
 * reminder that came due while the process was down for longer than that is not mailed by this
 * clock -- its moment is in no window -- but the morning letter still carries it, the inbox has
 * shown it all along, and the calendar subscription had the event. The runbook says so.
 */
@Component
public class ReminderScheduler {

    private static final Logger log = LoggerFactory.getLogger(ReminderScheduler.class);

    /** How far back the first tick after a boot reaches; one tick's worth by default. */
    static final Duration FIRST_WINDOW = Duration.ofMinutes(1);

    private final NotificationPushService push;
    private final ReminderMailService mail;
    private final PushDeliveryMetrics metrics;
    private final Clock clock;
    private OffsetDateTime lastTick;

    @Autowired
    public ReminderScheduler(NotificationPushService push, ReminderMailService mail,
            PushDeliveryMetrics metrics) {
        this(push, mail, metrics, Clock.systemUTC());
    }

    ReminderScheduler(NotificationPushService push, ReminderMailService mail,
            PushDeliveryMetrics metrics, Clock clock) {
        this.push = push;
        this.mail = mail;
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
        OffsetDateTime since = lastTick;
        boolean completed = true;
        try {
            int rung = push.pushDue(since, until);
            if (rung > 0) {
                log.info("reminder ring delivered to {} account(s)", rung);
            }
        } catch (RuntimeException e) {
            log.warn("the reminder clock could not read its audience for the ring; the window is retried", e);
            completed = false;
        }
        try {
            int mailed = mail.mailDue(since, until);
            if (mailed > 0) {
                log.info("reminder letter written for {} account(s)", mailed);
            }
        } catch (RuntimeException e) {
            log.warn("the reminder clock could not read its audience for the letter; the window is retried", e);
            completed = false;
        }
        if (!completed) {
            return;
        }
        lastTick = until;
        metrics.recordDueTick(until);
    }
}
