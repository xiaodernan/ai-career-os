package com.careeros.notification.service;

import com.careeros.application.repository.ApplicationRepository;
import com.careeros.auth.entity.User;
import com.careeros.auth.repository.UserRepository;
import com.careeros.mail.service.MailList;
import com.careeros.mail.service.MailPreferenceService;
import com.careeros.notification.dto.NotificationDtos.NotificationItem;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

/**
 * The minute clock's letter (roadmap 41.1): a reminder that comes due is mailed at its moment,
 * not at the next morning's sweep.
 *
 * <p>The audience is the board's own answer -- the accounts whose reminder fell inside the
 * tick's window, read through the same query the ring uses, so an alert that closed the row
 * (`offer`, `rejected`) is not mailed about work that is finished. What each account is mailed
 * is read from the inbox it already has: the due reminder's item, unread and unmailed, whose
 * moment falls in the same window. That is what keeps the letter, the inbox and the board one
 * story -- a reminder the reader already dismissed or read in the app is not mailed, and an
 * item the morning letter already carried is not mailed twice.
 *
 * <p>The latch is the episode's own ({@code notified_at}), the same row the morning sweep
 * writes: one reminder is one letter whichever pass carries it. It is written only after the
 * transport accepts, so a refusal is a warn line and the morning letter remains the fallback;
 * the window is the clock's, so a reminder the reader moved is a new episode and a new letter.
 *
 * <p>The letter is silent by design when the reader turned this dial off (roadmap 41.1) -- the
 * reminder still arrives in the morning signal letter, so "off" chooses the moment rather than
 * the silence. One account in a bad state is a warn line, never the rest of the tick.
 */
@Service
public class ReminderMailService {

    private static final Logger log = LoggerFactory.getLogger(ReminderMailService.class);

    private final NotificationService notifications;
    private final ReminderMailer mailer;
    private final ApplicationRepository applications;
    private final UserRepository users;
    private final NotificationDeliveryMetrics metrics;
    private final MailPreferenceService preferences;

    public ReminderMailService(NotificationService notifications, ReminderMailer mailer,
            ApplicationRepository applications, UserRepository users,
            NotificationDeliveryMetrics metrics, MailPreferenceService preferences) {
        this.notifications = notifications;
        this.mailer = mailer;
        this.applications = applications;
        this.users = users;
        this.metrics = metrics;
        this.preferences = preferences;
    }

    /** One tick's pass; returns how many mailboxes received a reminder letter. */
    public int mailDue(OffsetDateTime since, OffsetDateTime until) {
        int mailed = 0;
        Set<UUID> stopped = preferences.optedOut(MailList.REMINDERS);
        for (UUID userId : applications.findUserIdsWithReminderBetween(since, until)) {
            if (stopped.contains(userId)) {
                continue;
            }
            try {
                if (deliver(userId, since, until)) {
                    mailed++;
                }
            } catch (RuntimeException e) {
                log.warn("the reminder letter for {} could not be prepared", userId, e);
            }
        }
        return mailed;
    }

    private boolean deliver(UUID userId, OffsetDateTime since, OffsetDateTime until) {
        List<NotificationItem> due = notifications.awaitingDelivery(userId).stream()
                .filter(item -> NotificationService.KIND_REMINDER.equals(item.kind()))
                .filter(item -> item.at() != null && item.at().isAfter(since)
                        && !item.at().isAfter(until))
                .toList();
        if (due.isEmpty()) {
            return false;
        }
        Optional<User> account = users.findById(userId);
        if (account.isEmpty()) {
            log.warn("the reminder letter has no account to mail ({})", userId);
            return false;
        }
        String to = account.get().getEmail();
        if (to == null || to.isBlank()) {
            log.warn("the reminder letter has no address for {}", userId);
            return false;
        }
        try {
            mailer.send(userId, to, due, account.get().getLocale());
        } catch (RuntimeException e) {
            metrics.recordRefused();
            log.warn("the reminder letter to {} was refused", userId, e);
            return false;
        }
        OffsetDateTime acceptedAt = OffsetDateTime.now(ZoneOffset.UTC);
        metrics.recordSent(acceptedAt);
        notifications.markNotified(userId, due.stream().map(NotificationItem::key).toList(),
                acceptedAt);
        return true;
    }
}
