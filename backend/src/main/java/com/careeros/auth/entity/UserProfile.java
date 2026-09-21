package com.careeros.auth.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.annotations.UpdateTimestamp;
import org.hibernate.annotations.UuidGenerator;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "user_profiles")
public class UserProfile {

    @Id
    @UuidGenerator
    @Column(name = "id", nullable = false, updatable = false)
    private UUID id;

    @Column(name = "user_id", nullable = false, unique = true, updatable = false)
    private UUID userId;

    @Column(name = "headline")
    private String headline;

    @Column(name = "summary")
    private String summary;

    @Column(name = "location")
    private String location;

    @Column(name = "years_experience", precision = 4, scale = 1)
    private BigDecimal yearsExperience;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "target_roles", nullable = false)
    private List<String> targetRoles = List.of();

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "target_locations", nullable = false)
    private List<String> targetLocations = List.of();

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "links", nullable = false)
    private Map<String, Object> links = new HashMap<>();

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "work_authorization", nullable = false)
    private Map<String, Object> workAuthorization = new HashMap<>();

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "preferences", nullable = false)
    private Map<String, Object> preferences = new HashMap<>();

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

    public String getHeadline() {
        return headline;
    }

    public void setHeadline(String headline) {
        this.headline = headline;
    }

    public String getSummary() {
        return summary;
    }

    public void setSummary(String summary) {
        this.summary = summary;
    }

    public String getLocation() {
        return location;
    }

    public void setLocation(String location) {
        this.location = location;
    }

    public BigDecimal getYearsExperience() {
        return yearsExperience;
    }

    public void setYearsExperience(BigDecimal yearsExperience) {
        this.yearsExperience = yearsExperience;
    }

    public List<String> getTargetRoles() {
        return targetRoles;
    }

    public void setTargetRoles(List<String> targetRoles) {
        this.targetRoles = targetRoles == null ? List.of() : targetRoles;
    }

    public List<String> getTargetLocations() {
        return targetLocations;
    }

    public void setTargetLocations(List<String> targetLocations) {
        this.targetLocations = targetLocations == null ? List.of() : targetLocations;
    }

    public Map<String, Object> getLinks() {
        return links;
    }

    public void setLinks(Map<String, Object> links) {
        this.links = links == null ? new HashMap<>() : links;
    }

    public Map<String, Object> getWorkAuthorization() {
        return workAuthorization;
    }

    public void setWorkAuthorization(Map<String, Object> workAuthorization) {
        this.workAuthorization = workAuthorization == null ? new HashMap<>() : workAuthorization;
    }

    public Map<String, Object> getPreferences() {
        return preferences;
    }

    public void setPreferences(Map<String, Object> preferences) {
        this.preferences = preferences == null ? new HashMap<>() : preferences;
    }
}
