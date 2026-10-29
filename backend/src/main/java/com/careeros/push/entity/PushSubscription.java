package com.careeros.push.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.OffsetDateTime;
import java.util.UUID;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

/**
 * One browser's promise that its installed worker can be woken (roadmap 33.1).
 *
 * <p>The endpoint is the registration's identity, not this row's: it is the address a push
 * service gave the browser, and the unique constraint says one registration is one row. The
 * caller is therefore mutable -- a second reader opting in on the same browser re-points the
 * row rather than adding a second one, because two rows would ring that browser twice for one
 * morning. The keys travel with the subscription; the push sent today carries no payload, so
 * they are kept for the day one does.
 */
@Entity
@Table(name = "push_subscriptions")
public class PushSubscription {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(name = "user_id", nullable = false)
    private UUID userId;

    /** Named `endpointUrl` rather than `endpoint`: `getEndpoint()` is the storage knob's accessor. */
    @Column(name = "endpoint", nullable = false, columnDefinition = "text")
    private String endpointUrl;

    @Column(nullable = false, length = 160)
    private String p256dh;

    @Column(nullable = false, length = 64)
    private String auth;

    @Column(length = 120)
    private String label;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private OffsetDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private OffsetDateTime updatedAt;

    public UUID getId() {
        return id;
    }

    public UUID getUserId() {
        return userId;
    }

    public void setUserId(UUID userId) {
        this.userId = userId;
    }

    public String getEndpointUrl() {
        return endpointUrl;
    }

    public void setEndpointUrl(String endpointUrl) {
        this.endpointUrl = endpointUrl;
    }

    public String getP256dh() {
        return p256dh;
    }

    public void setP256dh(String p256dh) {
        this.p256dh = p256dh;
    }

    public String getAuth() {
        return auth;
    }

    public void setAuth(String auth) {
        this.auth = auth;
    }

    public String getLabel() {
        return label;
    }

    public void setLabel(String label) {
        this.label = label;
    }

    public OffsetDateTime getCreatedAt() {
        return createdAt;
    }

    public OffsetDateTime getUpdatedAt() {
        return updatedAt;
    }
}
