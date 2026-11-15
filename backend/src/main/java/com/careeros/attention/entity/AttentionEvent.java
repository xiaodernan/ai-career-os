package com.careeros.attention.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

/** The attention rows (Epic 267): a landed page, a dwell, an act -- never per-click noise. */
@Entity
@Table(name = "attention_events")
public class AttentionEvent {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(name = "user_id")
    private UUID userId;

    @Column(nullable = false)
    private String journey = "app";

    @Column(nullable = false)
    private String path;

    @Column(nullable = false)
    private String event;

    private String value;

    @Column(name = "created_at", nullable = false, insertable = false, updatable = false)
    private Instant createdAt;

    protected AttentionEvent() {
    }

    /** A new row to land in the ledger; the driver mints the id on flush. */
    public AttentionEvent(UUID userId, String journey, String path, String event, String value) {
        this.userId = userId;
        this.journey = journey == null ? "app" : journey;
        this.path = path;
        this.event = event;
        this.value = value;
        this.createdAt = Instant.now();
    }

    public UUID getId() { return id; }
    public UUID getUserId() { return userId; }
    public String getJourney() { return journey; }
    public String getPath() { return path; }
    public String getEvent() { return event; }
    public String getValue() { return value; }
    public Instant getCreatedAt() { return createdAt; }
}
