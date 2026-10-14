package com.careeros.ai.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.OffsetDateTime;
import java.util.Map;
import java.util.UUID;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

/**
 * One stored run of the growth report, keyed to the (user, target_role) pair the report
 * was built for. The row exists so the next run for the same role diffs against
 * something the server holds (roadmap 10.4) rather than against whatever the browser
 * still had in memory; the report itself stays the engine's schema, stored verbatim.
 */
@Entity
@Table(name = "growth_plans")
public class GrowthPlan {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(name = "user_id", nullable = false)
    private UUID userId;

    /** The role the report targeted, as the request spelled it — the diff's join key. */
    @Column(name = "target_role", nullable = false, length = 200)
    private String targetRole;

    /** The report's headline number, denormalized so a scan does not have to open the jsonb. */
    @Column(name = "coverage", nullable = false)
    private double coverage;

    /** The engine's own answer, verbatim. This row does not re-model it. */
    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "report", nullable = false, columnDefinition = "jsonb")
    private Map<String, Object> report;

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

    public String getTargetRole() {
        return targetRole;
    }

    public void setTargetRole(String targetRole) {
        this.targetRole = targetRole;
    }

    public double getCoverage() {
        return coverage;
    }

    public void setCoverage(double coverage) {
        this.coverage = coverage;
    }

    public Map<String, Object> getReport() {
        return report;
    }

    public void setReport(Map<String, Object> report) {
        this.report = report;
    }

    public OffsetDateTime getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(OffsetDateTime createdAt) {
        this.createdAt = createdAt;
    }
}
