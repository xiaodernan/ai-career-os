package com.careeros.resume.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.util.List;
import java.util.UUID;
import org.hibernate.annotations.UuidGenerator;

@Entity
@Table(name = "projects")
public class Project {

    @Id
    @UuidGenerator
    @Column(name = "id", nullable = false, updatable = false)
    private UUID id;

    @Column(name = "resume_version_id", nullable = false, updatable = false)
    private UUID resumeVersionId;

    @Column(name = "user_id", nullable = false, updatable = false)
    private UUID userId;

    @Column(name = "name", nullable = false)
    private String name;

    @Column(name = "role")
    private String role;

    @Column(name = "period")
    private String period;

    @Column(name = "bullets", nullable = false)
    private String[] bullets = new String[0];

    @Column(name = "tech", nullable = false)
    private String[] tech = new String[0];

    @Column(name = "url")
    private String url;

    @Column(name = "ordinal", nullable = false)
    private int ordinal;

    public UUID getId() {
        return id;
    }

    public UUID getResumeVersionId() {
        return resumeVersionId;
    }

    public void setResumeVersionId(UUID resumeVersionId) {
        this.resumeVersionId = resumeVersionId;
    }

    public UUID getUserId() {
        return userId;
    }

    public void setUserId(UUID userId) {
        this.userId = userId;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getRole() {
        return role;
    }

    public void setRole(String role) {
        this.role = role;
    }

    public String getPeriod() {
        return period;
    }

    public void setPeriod(String period) {
        this.period = period;
    }

    public List<String> getBullets() {
        return bullets == null ? List.of() : List.of(bullets);
    }

    public void setBullets(List<String> bullets) {
        this.bullets = bullets == null ? new String[0] : bullets.toArray(String[]::new);
    }

    public List<String> getTech() {
        return tech == null ? List.of() : List.of(tech);
    }

    public void setTech(List<String> tech) {
        this.tech = tech == null ? new String[0] : tech.toArray(String[]::new);
    }

    public String getUrl() {
        return url;
    }

    public void setUrl(String url) {
        this.url = url;
    }

    public int getOrdinal() {
        return ordinal;
    }

    public void setOrdinal(int ordinal) {
        this.ordinal = ordinal;
    }
}
