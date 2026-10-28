package com.careeros.mail.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.OffsetDateTime;
import java.util.UUID;
import org.hibernate.annotations.UpdateTimestamp;

/**
 * One account's answer to the two letters (roadmap 23.1).
 *
 * <p>There is no row until the reader says something, so absence means both letters are on:
 * signup writes nothing, a never-asked account and an account that kept both dials sit in the
 * same state, and an export of the mail settings is "what changed", not "what was defaulted".
 *
 * <p>The row is keyed by the account and the columns are the two letters by the names the
 * unsubscribe page prints, so the page, the sweeps and this table cannot drift apart the way a
 * renamed scheduler could.
 */
@Entity
@Table(name = "mail_preferences")
public class MailPreference {

    @Id
    @Column(name = "user_id", nullable = false, updatable = false)
    private UUID userId;

    /** The Monday letter: the week in applications, composed and mailed by the digest sweep. */
    @Column(name = "weekly_digest", nullable = false)
    private boolean weeklyDigest = true;

    /** The morning signals: the inbox's unread items, mailed once per episode. */
    @Column(name = "signal_mail", nullable = false)
    private boolean signalMail = true;

    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private OffsetDateTime updatedAt;

    public UUID getUserId() {
        return userId;
    }

    public void setUserId(UUID userId) {
        this.userId = userId;
    }

    public boolean isWeeklyDigest() {
        return weeklyDigest;
    }

    public void setWeeklyDigest(boolean weeklyDigest) {
        this.weeklyDigest = weeklyDigest;
    }

    public boolean isSignalMail() {
        return signalMail;
    }

    public void setSignalMail(boolean signalMail) {
        this.signalMail = signalMail;
    }

    public OffsetDateTime getUpdatedAt() {
        return updatedAt;
    }
}
