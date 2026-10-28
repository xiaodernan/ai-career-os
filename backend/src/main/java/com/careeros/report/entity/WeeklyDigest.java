package com.careeros.report.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.Map;
import java.util.UUID;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

/**
 * One week's letter (roadmap 19.4): the insight digest composed on the backend's clock and
 * kept as it came back, so the week's signals outlive the week.
 *
 * <p>The payload is the engine's answer verbatim -- the totals, the stage mix, the rates, the
 * stalled rows, the signals -- which is also the material the letter's mail is assembled from.
 * Keeping the composed answer rather than re-deriving it means the letter a reader opens in
 * December is the one September wrote, not a second reading of rows that have changed since.
 */
@Entity
@Table(name = "weekly_digests")
public class WeeklyDigest {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(name = "user_id", nullable = false, updatable = false)
    private UUID userId;

    /** The Monday the letter's week starts on; the constraint on the table holds it to one. */
    @Column(name = "week_start", nullable = false, updatable = false)
    private LocalDate weekStart;

    @Column(name = "window_days", nullable = false)
    private int windowDays;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "jsonb", nullable = false)
    private Map<String, Object> payload;

    @Column(name = "generated_at", nullable = false)
    private OffsetDateTime generatedAt;

    /** When the letter last left for its mailbox; the sweep's latch against a second copy. */
    @Column(name = "delivered_at")
    private OffsetDateTime deliveredAt;

    /** The transport's last refusal, cleared by a later success; null before the first try. */
    @Column(name = "delivery_error", length = 500)
    private String deliveryError;

    @Column(name = "delivery_attempts", nullable = false)
    private int deliveryAttempts;

    public UUID getId() {
        return id;
    }

    public UUID getUserId() {
        return userId;
    }

    public void setUserId(UUID userId) {
        this.userId = userId;
    }

    public LocalDate getWeekStart() {
        return weekStart;
    }

    public void setWeekStart(LocalDate weekStart) {
        this.weekStart = weekStart;
    }

    public int getWindowDays() {
        return windowDays;
    }

    public void setWindowDays(int windowDays) {
        this.windowDays = windowDays;
    }

    public Map<String, Object> getPayload() {
        return payload;
    }

    public void setPayload(Map<String, Object> payload) {
        this.payload = payload;
    }

    public OffsetDateTime getGeneratedAt() {
        return generatedAt;
    }

    public void setGeneratedAt(OffsetDateTime generatedAt) {
        this.generatedAt = generatedAt;
    }

    public OffsetDateTime getDeliveredAt() {
        return deliveredAt;
    }

    public void setDeliveredAt(OffsetDateTime deliveredAt) {
        this.deliveredAt = deliveredAt;
    }

    public String getDeliveryError() {
        return deliveryError;
    }

    public void setDeliveryError(String deliveryError) {
        this.deliveryError = deliveryError;
    }

    public int getDeliveryAttempts() {
        return deliveryAttempts;
    }

    public void setDeliveryAttempts(int deliveryAttempts) {
        this.deliveryAttempts = deliveryAttempts;
    }
}
