package com.careeros.inbound.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.OffsetDateTime;
import java.util.UUID;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UuidGenerator;

/**
 * One letter a provider forwarded to an account's inbound address (roadmap 37.1).
 *
 * <p>The row keeps what the webhook measured, copied rather than joined: a letter is the
 * reader's record of what a recruiter wrote, so it must not change when the mail provider's
 * copy expires or the account later deletes something else. The message key is the
 * provider's MessageID, or a digest of the fields when the payload carried none, and the
 * unique pair with the account is what makes a retry one letter rather than two.
 */
@Entity
@Table(name = "inbound_mails")
public class InboundMail {

    @Id
    @UuidGenerator
    @Column(name = "id", nullable = false, updatable = false)
    private UUID id;

    @Column(name = "user_id", nullable = false, updatable = false)
    private UUID userId;

    @Column(name = "message_key", nullable = false, updatable = false)
    private String messageKey;

    @Column(name = "from_address", nullable = false)
    private String fromAddress;

    @Column(name = "subject", nullable = false)
    private String subject;

    @Column(name = "body_text", nullable = false)
    private String bodyText;

    /** The classifier's reading (37.2); null when it could not answer, never "nothing to read". */
    @Column(name = "intent", length = 16)
    private String intent;

    @Column(name = "company", length = 200)
    private String company;

    @Column(name = "role", length = 200)
    private String role;

    /**
     * The application this letter answers (37.3); null while it waits unmatched. The link is a
     * pointer to the reader's own card, so deleting the card clears the column rather than the
     * letter -- a reply is the reader's record of what a recruiter wrote.
     */
    @Column(name = "application_id")
    private UUID applicationId;

    @Column(name = "filed_at")
    private OffsetDateTime filedAt;

    @Column(name = "received_at", nullable = false)
    private OffsetDateTime receivedAt;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private OffsetDateTime createdAt;

    public UUID getId() {
        return id;
    }

    public UUID getUserId() {
        return userId;
    }

    public void setUserId(UUID userId) {
        this.userId = userId;
    }

    public String getMessageKey() {
        return messageKey;
    }

    public void setMessageKey(String messageKey) {
        this.messageKey = messageKey;
    }

    public String getFromAddress() {
        return fromAddress;
    }

    public void setFromAddress(String fromAddress) {
        this.fromAddress = fromAddress;
    }

    public String getSubject() {
        return subject;
    }

    public void setSubject(String subject) {
        this.subject = subject;
    }

    public String getBodyText() {
        return bodyText;
    }

    public void setBodyText(String bodyText) {
        this.bodyText = bodyText;
    }

    public String getIntent() {
        return intent;
    }

    public void setIntent(String intent) {
        this.intent = intent;
    }

    public String getCompany() {
        return company;
    }

    public void setCompany(String company) {
        this.company = company;
    }

    public String getRole() {
        return role;
    }

    public void setRole(String role) {
        this.role = role;
    }

    public UUID getApplicationId() {
        return applicationId;
    }

    public void setApplicationId(UUID applicationId) {
        this.applicationId = applicationId;
    }

    public OffsetDateTime getFiledAt() {
        return filedAt;
    }

    public void setFiledAt(OffsetDateTime filedAt) {
        this.filedAt = filedAt;
    }

    public OffsetDateTime getReceivedAt() {
        return receivedAt;
    }

    public void setReceivedAt(OffsetDateTime receivedAt) {
        this.receivedAt = receivedAt;
    }

    public OffsetDateTime getCreatedAt() {
        return createdAt;
    }
}
