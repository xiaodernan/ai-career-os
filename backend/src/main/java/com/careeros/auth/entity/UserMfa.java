package com.careeros.auth.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.OffsetDateTime;
import java.util.UUID;
import org.hibernate.annotations.CreationTimestamp;

/**
 * One account's second factor (roadmap 36.1): the TOTP seed, sealed, and how far its codes
 * have been spent.
 *
 * <p>The row exists from the moment enrollment starts, so a reader can come back and finish
 * it in another tab; {@code active} is what separates a promise from a lock. {@code lastUsedStep}
 * is the replay guard the sign-in check advances -- a code that opened the door once cannot
 * open it again while its step is still in the window.
 */
@Entity
@Table(name = "user_mfa")
public class UserMfa {

    @Id
    @Column(name = "user_id", nullable = false, updatable = false)
    private UUID userId;

    @Column(name = "secret_ciphertext", nullable = false)
    private String secretCiphertext;

    @Column(name = "active", nullable = false)
    private boolean active;

    @Column(name = "last_used_step")
    private Long lastUsedStep;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private OffsetDateTime createdAt;

    @Column(name = "activated_at")
    private OffsetDateTime activatedAt;

    public UUID getUserId() {
        return userId;
    }

    public void setUserId(UUID userId) {
        this.userId = userId;
    }

    public String getSecretCiphertext() {
        return secretCiphertext;
    }

    public void setSecretCiphertext(String secretCiphertext) {
        this.secretCiphertext = secretCiphertext;
    }

    public boolean isActive() {
        return active;
    }

    public void setActive(boolean active) {
        this.active = active;
    }

    public Long getLastUsedStep() {
        return lastUsedStep;
    }

    public void setLastUsedStep(Long lastUsedStep) {
        this.lastUsedStep = lastUsedStep;
    }

    public OffsetDateTime getCreatedAt() {
        return createdAt;
    }

    public OffsetDateTime getActivatedAt() {
        return activatedAt;
    }

    public void setActivatedAt(OffsetDateTime activatedAt) {
        this.activatedAt = activatedAt;
    }
}
