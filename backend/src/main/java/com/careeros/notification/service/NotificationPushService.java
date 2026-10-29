package com.careeros.notification.service;

import com.careeros.notification.dto.NotificationDtos.NotificationItem;
import com.careeros.push.entity.PushSubscription;
import com.careeros.push.repository.PushSubscriptionRepository;
import com.careeros.push.service.PushDeliveryMetrics;
import com.careeros.push.service.PushSender;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

/**
 * The morning sweep that rings the reader's browsers (roadmap 33.3).
 *
 * <p>The audience is every account with at least one registration -- the browser is the consent,
 * so this pass never reads the mail stop list; a reader who turned the letter off asked for the
 * ring instead. Each account is asked what is still unread, undismissed and not yet pushed; an
 * empty answer is the common morning and costs no outbound call. What a browser is told is only
 * <em>that</em> something is waiting: the push carries no payload, and the worker asks the
 * authenticated inbox when it wakes. One account therefore gets one coalesced ring fanned to
 * each of its browsers, even when the inbox holds five items.
 *
 * <p>The latch is the episode's own ({@code pushed_at}, roadmap 33.3's migration), not the
 * letter's: a reader who has not opened the app since yesterday's letter is exactly who a ring
 * is for, and a reader who read the letter in the app is not rung about it. It is written only
 * when at least one browser accepted -- a morning where every registration refused is not
 * remembered as rung, so the next morning tries again -- and a refusal is metered, not retried
 * in place, for the reason 33.2 gives: one pass is one attempt per registration.
 *
 * <p>A {@code GONE} registration is deleted here, because a push service that says the
 * registration no longer exists will say it every morning; keeping the row would make the sweep
 * walk a dead browser forever and ring nothing. One account in a bad state is a warn line, never
 * the rest of the morning: the other accounts still ring.
 */
@Service
public class NotificationPushService {

    private static final Logger log = LoggerFactory.getLogger(NotificationPushService.class);

    private final NotificationService notifications;
    private final PushSender sender;
    private final PushSubscriptionRepository subscriptions;
    private final PushDeliveryMetrics metrics;

    public NotificationPushService(NotificationService notifications, PushSender sender,
            PushSubscriptionRepository subscriptions, PushDeliveryMetrics metrics) {
        this.notifications = notifications;
        this.sender = sender;
        this.subscriptions = subscriptions;
        this.metrics = metrics;
    }

    /** One morning's ring pass; returns how many accounts were woken on at least one browser. */
    public int pushPending() {
        int rung = 0;
        for (UUID userId : subscriptions.distinctUserIds()) {
            try {
                if (ring(userId)) {
                    rung++;
                }
            } catch (RuntimeException e) {
                log.warn("the morning ring for {} could not be prepared", userId, e);
            }
        }
        return rung;
    }

    private boolean ring(UUID userId) {
        List<NotificationItem> waiting = notifications.awaitingPush(userId);
        if (waiting.isEmpty()) {
            return false;
        }
        List<PushSubscription> browsers = subscriptions.findByUserIdOrderByCreatedAtDesc(userId);
        List<PushSubscription> retired = new ArrayList<>();
        boolean accepted = false;
        for (PushSubscription browser : browsers) {
            PushSender.Outcome outcome = sender.send(browser);
            metrics.record(outcome);
            if (outcome == PushSender.Outcome.SENT) {
                accepted = true;
            }
            if (outcome == PushSender.Outcome.GONE) {
                retired.add(browser);
            }
        }
        if (!retired.isEmpty()) {
            subscriptions.deleteAll(retired);
        }
        if (!accepted) {
            return false;
        }
        notifications.markPushed(userId,
                waiting.stream().map(NotificationItem::key).toList(),
                OffsetDateTime.now(ZoneOffset.UTC));
        return true;
    }
}
