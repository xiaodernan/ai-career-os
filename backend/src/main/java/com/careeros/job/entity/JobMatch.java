package com.careeros.job.entity;

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
import org.hibernate.type.SqlTypes;

/** Written by ai-service (match feature); the backend only reads this table. */
@Entity
@Table(name = "job_matches")
public class JobMatch {

    @Id
    @Column(name = "id", nullable = false, updatable = false)
    private UUID id;

    @Column(name = "user_id", nullable = false, updatable = false)
    private UUID userId;

    @Column(name = "job_id", nullable = false, updatable = false)
    private UUID jobId;

    @Column(name = "resume_version_id", nullable = false, updatable = false)
    private UUID resumeVersionId;

    @Column(name = "overall", nullable = false)
    private float overall;

    @Column(name = "technical", nullable = false)
    private float technical;

    @Column(name = "experience", nullable = false)
    private float experience;

    @Column(name = "projects", nullable = false)
    private float projects;

    @Column(name = "education", nullable = false)
    private float education;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "matched_skills", nullable = false)
    private List<Object> matchedSkills = List.of();

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "missing_skills", nullable = false)
    private List<Object> missingSkills = List.of();

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "evidence", nullable = false)
    private List<Object> evidence = List.of();

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "why_match", nullable = false)
    private List<Object> whyMatch = List.of();

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "preparation", nullable = false)
    private List<Object> preparation = List.of();

    @Column(name = "narrative")
    private String narrative;

    @Column(name = "model")
    private String model;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private OffsetDateTime createdAt;

    public UUID getId() {
        return id;
    }

    public UUID getUserId() {
        return userId;
    }

    public UUID getJobId() {
        return jobId;
    }

    public UUID getResumeVersionId() {
        return resumeVersionId;
    }

    public float getOverall() {
        return overall;
    }

    public float getTechnical() {
        return technical;
    }

    public float getExperience() {
        return experience;
    }

    public float getProjects() {
        return projects;
    }

    public float getEducation() {
        return education;
    }

    public List<Object> getMatchedSkills() {
        return matchedSkills;
    }

    public List<Object> getMissingSkills() {
        return missingSkills;
    }

    public List<Object> getEvidence() {
        return evidence;
    }

    public List<Object> getWhyMatch() {
        return whyMatch;
    }

    public List<Object> getPreparation() {
        return preparation;
    }

    public String getNarrative() {
        return narrative;
    }

    public String getModel() {
        return model;
    }

    public OffsetDateTime getCreatedAt() {
        return createdAt;
    }
}
