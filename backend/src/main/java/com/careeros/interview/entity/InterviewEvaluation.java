package com.careeros.interview.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.annotations.UuidGenerator;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "interview_evaluations")
public class InterviewEvaluation {

    @Id
    @UuidGenerator
    @Column(name = "id", nullable = false, updatable = false)
    private UUID id;

    @Column(name = "session_id", nullable = false, unique = true, updatable = false)
    private UUID sessionId;

    @Column(name = "user_id", nullable = false, updatable = false)
    private UUID userId;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "dims", nullable = false)
    private Map<String, Object> dims = Map.of();

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "summary", nullable = false)
    private Map<String, Object> summary = Map.of();

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "trajectory", nullable = false)
    private List<Object> trajectory = List.of();

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private OffsetDateTime createdAt;

    public UUID getId() {
        return id;
    }

    public UUID getSessionId() {
        return sessionId;
    }

    public void setSessionId(UUID sessionId) {
        this.sessionId = sessionId;
    }

    public UUID getUserId() {
        return userId;
    }

    public void setUserId(UUID userId) {
        this.userId = userId;
    }

    public Map<String, Object> getDims() {
        return dims;
    }

    public void setDims(Map<String, Object> dims) {
        this.dims = dims == null ? Map.of() : dims;
    }

    public Map<String, Object> getSummary() {
        return summary;
    }

    public void setSummary(Map<String, Object> summary) {
        this.summary = summary == null ? Map.of() : summary;
    }

    public List<Object> getTrajectory() {
        return trajectory;
    }

    public void setTrajectory(List<Object> trajectory) {
        this.trajectory = trajectory == null ? List.of() : trajectory;
    }

    public OffsetDateTime getCreatedAt() {
        return createdAt;
    }
}
