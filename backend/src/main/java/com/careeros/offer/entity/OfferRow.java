package com.careeros.offer.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EntityListeners;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;
import java.time.OffsetDateTime;
import java.util.UUID;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

/**
 * One offer the reader holds (Epic 185): the shelf row the compare view reads instead
 * of re-entered numbers. Equity is stored annualized — the compare action already did
 * the vest arithmetic, and the shelf keeps its result.
 */
@Entity
@Table(name = "offers")
public class OfferRow {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @Column(name = "id", nullable = false, updatable = false)
    private UUID id;

    @Column(name = "user_id", nullable = false, updatable = false)
    private UUID userId;

    @Column(name = "label", nullable = false, length = 120)
    private String label;

    @Column(name = "base", nullable = false)
    private int base;

    @Column(name = "bonus", nullable = false)
    private int bonus;

    @Column(name = "equity", nullable = false)
    private int equity;

    @Column(name = "currency", nullable = false, length = 3)
    private String currency = "USD";

    /** onsite|hybrid|remote — the jobs vocabulary, so the shelf spells what the board spells. */
    @Column(name = "remote_type", nullable = false, length = 16)
    private String remoteType = "onsite";

    @Column(name = "deadline")
    private OffsetDateTime deadline;

    @Column(name = "notes")
    private String notes;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private OffsetDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private OffsetDateTime updatedAt;

    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }
    public UUID getUserId() { return userId; }
    public void setUserId(UUID userId) { this.userId = userId; }
    public String getLabel() { return label; }
    public void setLabel(String label) { this.label = label; }
    public int getBase() { return base; }
    public void setBase(int base) { this.base = base; }
    public int getBonus() { return bonus; }
    public void setBonus(int bonus) { this.bonus = bonus; }
    public int getEquity() { return equity; }
    public void setEquity(int equity) { this.equity = equity; }
    public String getCurrency() { return currency; }
    public void setCurrency(String currency) { this.currency = currency; }
    public String getRemoteType() { return remoteType; }
    public void setRemoteType(String remoteType) { this.remoteType = remoteType; }
    public OffsetDateTime getDeadline() { return deadline; }
    public void setDeadline(OffsetDateTime deadline) { this.deadline = deadline; }
    public String getNotes() { return notes; }
    public void setNotes(String notes) { this.notes = notes; }
    public OffsetDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(OffsetDateTime createdAt) { this.createdAt = createdAt; }
    public OffsetDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(OffsetDateTime updatedAt) { this.updatedAt = updatedAt; }

    /** The one number a reader compares offers by: cash plus the annualized equity. */
    public int totalComp() {
        return base + bonus + equity;
    }
}
