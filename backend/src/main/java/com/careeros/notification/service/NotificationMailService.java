package com.careeros.notification.service;

import com.careeros.application.repository.ApplicationRepository;
import com.careeros.auth.entity.User;
import com.careeros.auth.repository.UserRepository;
import com.careeros.job.repository.IngestionFeedRepository;
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
 * on the board and accounts subscribing to a feed, unioned so one account is one letter. Each
 * account is asked what is still waiting -- unread in the app and never mailed -- and an empty
 * answer is the common case, which is why the sweep never writes an empty letter.
 *
 * <p>The latch is written only after the transport accepts: a refused or missing account is a
 * warn line and the next morning tries again, while an accepted letter is remembered on the
 * episode, so a second run over the same morning cannot put a second copy in a mailbox. The
 * sweep holds no transaction across a send -- {@link NotificationService} opens its own around
 * the read and around the latch -- so a slow relay cannot pin a database connection.
 *
 * <p>One account in a bad state is a warn line, never the rest of the morning: the other
 * accounts still get their letters.
 */
@Service
public class NotificationMailService {

    private static final Logger log = LoggerFactory.getLogger(NotificationMailService.class);

    private final NotificationService notifications;
    private final NotificationMailer mailer;
    private final ApplicationRepository applications;
    private final IngestionFeedRepository feeds;
    private final UserRepository users;

    public NotificationMailService(NotificationService notifications, NotificationMailer mailer,
            ApplicationRepository applications, IngestionFeedRepository feeds,
            UserRepository users) {
        this.notifications = notifications;
        this.mailer = mailer;
        this.applications = applications;
        this.feeds = feeds;
        this.users = users;
    }

    /** One morning's pass; returns how many mailboxes received a letter. */
    public int mailPending() {
        int mailed = 0;
        for (UUID userId : audience()) {
            try {
                if (deliver(userId)) {
                    mailed++;
                }
            } catch (RuntimeException e) {
                log.warn("the signal mail for {} could not be prepared", userId, e);
            }
        }
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
            mailer.send(to, waiting, account.get().getLocale());
        } catch (RuntimeException e) {
            log.warn("the signal mail to {} was refused", userId, e);
            return false;
        }
        notifications.markNotified(userId, waiting.stream().map(NotificationItem::key).toList(),
                OffsetDateTime.now(ZoneOffset.UTC));
        return true;
    }

    /** The two kinds of account that can have a signal, each once. */
    private List<UUID> audience() {
        Set<UUID> out = new LinkedHashSet<>(applications.distinctUserIds());
        out.addAll(feeds.distinctUserIds());
        return List.copyOf(out);
    }
}
