package com.careeros.application.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.OffsetDateTime;
import java.util.UUID;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UuidGenerator;

@Entity
@Table(name = "applications")
public class Application {

    @Id
    @UuidGenerator
    @Column(name = "id", nullable = false, updatable = false)
    private UUID id;

    @Column(name = "user_id", nullable = false, updatable = false)
    private UUID userId;

    @Column(name = "job_id")
    private UUID jobId;

    @Column(name = "company_id")
    private UUID companyId;

    @Column(name = "title", nullable = false)
    private String title;

    @Column(name = "company_name")
    private String companyName;

    @Column(name = "status", nullable = false)
    private String status = "saved";

    @Column(name = "position", nullable = false)
    private int position;

    @Column(name = "notes")
    private String notes;

    @Column(name = "reminder_at")
    private OffsetDateTime reminderAt;

    @Column(name = "resume_version_id")
    private UUID resumeVersionId;

    @Column(name = "jd_id")
    private UUID jdId;

    @Column(name = "match_id")
    private UUID matchId;

    @Column(name = "offer_compensation")
    private String offerCompensation;

    @Column(name = "rejection_reason")
    private String rejectionReason;

    @Column(name = "applied_at")
    private OffsetDateTime appliedAt;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private OffsetDateTime createdAt;

    @Column(name = "updated_at", insertable = false, updatable = false)
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

    public UUID getJobId() {
        return jobId;
    }

    public void setJobId(UUID jobId) {
        this.jobId = jobId;
    }

    public UUID getCompanyId() {
        return companyId;
    }

    public void setCompanyId(UUID companyId) {
        this.companyId = companyId;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public String getCompanyName() {
        return companyName;
    }

    public void setCompanyName(String companyName) {
        this.companyName = companyName;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public int getPosition() {
        return position;
    }

    public void setPosition(int position) {
        this.position = position;
    }

    public String getNotes() {
        return notes;
    }

    public void setNotes(String notes) {
        this.notes = notes;
    }

    public OffsetDateTime getReminderAt() {
        return reminderAt;
    }

    public void setReminderAt(OffsetDateTime reminderAt) {
        this.reminderAt = reminderAt;
    }

    public UUID getResumeVersionId() {
        return resumeVersionId;
    }

    public void setResumeVersionId(UUID resumeVersionId) {
        this.resumeVersionId = resumeVersionId;
    }

    public UUID getJdId() {
        return jdId;
    }

    public void setJdId(UUID jdId) {
        this.jdId = jdId;
    }

    public UUID getMatchId() {
        return matchId;
    }

    public void setMatchId(UUID matchId) {
        this.matchId = matchId;
    }

    public String getOfferCompensation() {
        return offerCompensation;
    }

    public void setOfferCompensation(String offerCompensation) {
        this.offerCompensation = offerCompensation;
    }

    public String getRejectionReason() {
        return rejectionReason;
    }

    public void setRejectionReason(String rejectionReason) {
        this.rejectionReason = rejectionReason;
    }

    public OffsetDateTime getAppliedAt() {
        return appliedAt;
    }

    public void setAppliedAt(OffsetDateTime appliedAt) {
        this.appliedAt = appliedAt;
    }

    public OffsetDateTime getCreatedAt() {
        return createdAt;
    }

    public OffsetDateTime getUpdatedAt() {
        return updatedAt;
    }
}
