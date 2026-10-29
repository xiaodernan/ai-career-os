package com.careeros.notification.service;

import com.careeros.application.repository.ApplicationRepository;
import com.careeros.auth.entity.User;
import com.careeros.auth.repository.UserRepository;
import com.careeros.job.repository.IngestionFeedRepository;
import com.careeros.job.repository.SavedSearchRepository;
import com.careeros.mail.service.MailList;
import com.careeros.mail.service.MailPreferenceService;
import com.careeros.notification.dto.NotificationDtos.NotificationItem;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

/**
 * The morning sweep that carries the inbox out of the app (roadmap 22.1).
 *
 * <p>The audience is everyone the inbox could have something for: accounts with an application
 * on the board, accounts subscribing to a feed, and accounts keeping a saved search, unioned so
 * one account is one letter, minus the accounts that turned this letter off (roadmap 23.1). The
 * third half is what makes a saved search's voice reach a reader who only browses: with no
 * application and no feed they were in neither of the old halves, and the news waited for them
 * to open the app. An opt-out is read once per pass rather than per account, and it is silent by
 * design -- a reader who asked for quiet is not a warn line. Each remaining account is asked what
 * is still waiting -- unread in the app and never mailed -- and an empty answer is the common
 * case, which is why the sweep never writes an empty letter.
 *
 * <p>The latch is written only after the transport accepts: a refused or missing account is a
 * warn line and the next morning tries again, while an accepted letter is remembered on the
 * episode, so a second run over the same morning cannot put a second copy in a mailbox. The
 * sweep holds no transaction across a send -- {@link NotificationService} opens its own around
 * the read and around the latch -- so a slow relay cannot pin a database connection.
 *
 * <p>One account in a bad state is a warn line, never the rest of the morning: the other
 * accounts still get their letters. Every attempt that reached the transport is metered
 * (roadmap 22.2), so a relay that refuses the morning is visible to the scrape and the alarm
 * can tell it apart from an install whose inboxes are simply quiet. A finished pass moves the
 * sweep heartbeat (roadmap 22.3) even when no account had a letter, so a clock that stopped is
 * visible too; a pass that could not read its audience never reaches it.
 */
@Service
public class NotificationMailService {

    private static final Logger log = LoggerFactory.getLogger(NotificationMailService.class);

    private final NotificationService notifications;
    private final NotificationMailer mailer;
    private final ApplicationRepository applications;
    private final IngestionFeedRepository feeds;
    private final SavedSearchRepository savedSearches;
    private final UserRepository users;
    private final NotificationDeliveryMetrics metrics;
    private final MailPreferenceService preferences;

    public NotificationMailService(NotificationService notifications, NotificationMailer mailer,
            ApplicationRepository applications, IngestionFeedRepository feeds,
            SavedSearchRepository savedSearches,
            UserRepository users, NotificationDeliveryMetrics metrics,
            MailPreferenceService preferences) {
        this.notifications = notifications;
        this.mailer = mailer;
        this.applications = applications;
        this.feeds = feeds;
        this.savedSearches = savedSearches;
        this.users = users;
        this.metrics = metrics;
        this.preferences = preferences;
    }

    /** One morning's pass; returns how many mailboxes received a letter. */
    public int mailPending() {
        int mailed = 0;
        Set<UUID> stopped = preferences.optedOut(MailList.SIGNALS);
        for (UUID userId : audience()) {
            if (stopped.contains(userId)) {
                continue;
            }
            try {
                if (deliver(userId)) {
                    mailed++;
                }
            } catch (RuntimeException e) {
                log.warn("the signal mail for {} could not be prepared", userId, e);
            }
        }
        metrics.recordSweep(OffsetDateTime.now(ZoneOffset.UTC));
        return mailed;
    }

    private boolean deliver(UUID userId) {
        List<NotificationItem> waiting = notifications.awaitingDelivery(userId);
        if (waiting.isEmpty()) {
            return false;
        }
        Optional<User> account = users.findById(userId);
        if (account.isEmpty()) {
            log.warn("the signal mail has no account to mail ({})", userId);
            return false;
        }
        String to = account.get().getEmail();
        if (to == null || to.isBlank()) {
            log.warn("the signal mail has no address for {}", userId);
            return false;
        }
        try {
            mailer.send(userId, to, waiting, account.get().getLocale());
        } catch (RuntimeException e) {
            metrics.recordRefused();
            log.warn("the signal mail to {} was refused", userId, e);
            return false;
        }
        OffsetDateTime acceptedAt = OffsetDateTime.now(ZoneOffset.UTC);
        metrics.recordSent(acceptedAt);
        notifications.markNotified(userId, waiting.stream().map(NotificationItem::key).toList(),
                acceptedAt);
        return true;
    }

    /** The three kinds of account that can have a signal, each once. */
    private List<UUID> audience() {
        Set<UUID> out = new LinkedHashSet<>(applications.distinctUserIds());
        out.addAll(feeds.distinctUserIds());
        out.addAll(savedSearches.distinctUserIds());
        return List.copyOf(out);
    }
}
