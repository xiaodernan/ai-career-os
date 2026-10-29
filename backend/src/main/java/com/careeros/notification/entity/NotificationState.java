package com.careeros.notification.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.IdClass;
import jakarta.persistence.Table;
import java.io.Serializable;
import java.time.OffsetDateTime;
import java.util.Objects;
import java.util.UUID;
import org.hibernate.annotations.UpdateTimestamp;

/**
 * What one reader did with one synthesized notification (roadmap 19.3).
 *
 * <p>The notification itself is not a row -- it is read off the signals the platform already
 * keeps (an application waiting on the user, a pull the sweep recorded), so it cannot go stale
 * against its source. This row is only the state that has nowhere else to live: read,
 * dismissed, or carried out of the app by mail (roadmap 22.1). The key identifies the episode
 * rather than the underlying row, so a new episode of the same kind arrives unread, and a row
 * for an episode that ended simply stops being asked about.
 */
@Entity
@Table(name = "notification_states")
@IdClass(NotificationState.Key.class)
public class NotificationState {

    @Id
    @Column(name = "user_id", nullable = false)
    private UUID userId;

    @Id
    @Column(name = "signal_key", nullable = false, length = 160)
    private String signalKey;

    @Column(name = "read_at")
    private OffsetDateTime readAt;

    @Column(name = "dismissed_at")
    private OffsetDateTime dismissedAt;

    /** When a mail carrying this episode was accepted; null means it has only lived in the app. */
    @Column(name = "notified_at")
    private OffsetDateTime notifiedAt;

    /**
     * When a browser was woken for this episode (roadmap 33.3); null means its ring has not
     * happened. Separate from {@link #notifiedAt} because the letter and the ring are different
     * doors out of the app, with different consent and different failures.
     */
    @Column(name = "pushed_at")
    private OffsetDateTime pushedAt;

    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private OffsetDateTime updatedAt;

    public UUID getUserId() {
        return userId;
    }

    public void setUserId(UUID userId) {
        this.userId = userId;
    }

    public String getSignalKey() {
        return signalKey;
    }

    public void setSignalKey(String signalKey) {
        this.signalKey = signalKey;
    }

    public OffsetDateTime getReadAt() {
        return readAt;
    }

    public void setReadAt(OffsetDateTime readAt) {
        this.readAt = readAt;
    }

    public OffsetDateTime getDismissedAt() {
        return dismissedAt;
    }

    public void setDismissedAt(OffsetDateTime dismissedAt) {
        this.dismissedAt = dismissedAt;
    }

    public OffsetDateTime getNotifiedAt() {
        return notifiedAt;
    }

    public void setNotifiedAt(OffsetDateTime notifiedAt) {
        this.notifiedAt = notifiedAt;
    }

    public OffsetDateTime getPushedAt() {
        return pushedAt;
    }

    public void setPushedAt(OffsetDateTime pushedAt) {
        this.pushedAt = pushedAt;
    }

    public OffsetDateTime getUpdatedAt() {
        return updatedAt;
    }

    /** The composite identity JPA needs; never constructed by the application. */
    public static class Key implements Serializable {

        private UUID userId;
        private String signalKey;

        public Key() {
        }

        public Key(UUID userId, String signalKey) {
            this.userId = userId;
            this.signalKey = signalKey;
        }

        @Override
        public boolean equals(Object other) {
            if (this == other) {
                return true;
            }
            if (!(other instanceof Key key)) {
                return false;
            }
            return Objects.equals(userId, key.userId) && Objects.equals(signalKey, key.signalKey);
        }

        @Override
        public int hashCode() {
            return Objects.hash(userId, signalKey);
        }
    }
}
