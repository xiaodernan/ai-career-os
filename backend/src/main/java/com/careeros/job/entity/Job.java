package com.careeros.job.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UuidGenerator;

@Entity
@Table(name = "jobs")
public class Job {

    @Id
    @UuidGenerator
    @Column(name = "id", nullable = false, updatable = false)
    private UUID id;

    @Column(name = "company_id", nullable = false, updatable = false)
    private UUID companyId;

    @Column(name = "title", nullable = false)
    private String title;

    @Column(name = "location")
    private String location;

    @Column(name = "remote_type", nullable = false)
    private String remoteType = "onsite";

    @Column(name = "employment_type", nullable = false)
    private String employmentType = "full_time";

    @Column(name = "salary_min")
    private Integer salaryMin;

    @Column(name = "salary_max")
    private Integer salaryMax;

    @Column(name = "salary_currency", nullable = false)
    private String salaryCurrency = "CNY";

    @Column(name = "experience_years")
    private Integer experienceYears;

    @Column(name = "description", nullable = false)
    private String description;

    @Column(name = "requirements", nullable = false)
    private String[] requirements = new String[0];

    @Column(name = "nice_to_have", nullable = false)
    private String[] niceToHave = new String[0];

    @Column(name = "responsibilities", nullable = false)
    private String[] responsibilities = new String[0];

    @Column(name = "skills", nullable = false)
    private String[] skills = new String[0];

    @Column(name = "status", nullable = false)
    private String status = "open";

    @Column(name = "source", nullable = false)
    private String source = "user_paste";

    @Column(name = "external_url")
    private String externalUrl;

    @CreationTimestamp
    @Column(name = "posted_at", nullable = false, updatable = false)
    private OffsetDateTime postedAt;

    public UUID getId() {
        return id;
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

    public String getLocation() {
        return location;
    }

    public void setLocation(String location) {
        this.location = location;
    }

    public String getRemoteType() {
        return remoteType;
    }

    public void setRemoteType(String remoteType) {
        this.remoteType = remoteType;
    }

    public String getEmploymentType() {
        return employmentType;
    }

    public void setEmploymentType(String employmentType) {
        this.employmentType = employmentType;
    }

    public Integer getSalaryMin() {
        return salaryMin;
    }

    public void setSalaryMin(Integer salaryMin) {
        this.salaryMin = salaryMin;
    }

    public Integer getSalaryMax() {
        return salaryMax;
    }

    public void setSalaryMax(Integer salaryMax) {
        this.salaryMax = salaryMax;
    }

    public String getSalaryCurrency() {
        return salaryCurrency;
    }

    public void setSalaryCurrency(String salaryCurrency) {
        this.salaryCurrency = salaryCurrency;
    }

    public Integer getExperienceYears() {
        return experienceYears;
    }

    public void setExperienceYears(Integer experienceYears) {
        this.experienceYears = experienceYears;
    }

    public String getDescription() {
        return description;
    }

    public void setDescription(String description) {
        this.description = description;
    }

    public List<String> getRequirements() {
        return requirements == null ? List.of() : List.of(requirements);
    }

    public void setRequirements(List<String> requirements) {
        this.requirements = requirements == null ? new String[0] : requirements.toArray(String[]::new);
    }

    public List<String> getNiceToHave() {
        return niceToHave == null ? List.of() : List.of(niceToHave);
    }

    public void setNiceToHave(List<String> niceToHave) {
        this.niceToHave = niceToHave == null ? new String[0] : niceToHave.toArray(String[]::new);
    }

    public List<String> getResponsibilities() {
        return responsibilities == null ? List.of() : List.of(responsibilities);
    }

    public void setResponsibilities(List<String> responsibilities) {
        this.responsibilities = responsibilities == null ? new String[0] : responsibilities.toArray(String[]::new);
    }

    public List<String> getSkills() {
        return skills == null ? List.of() : List.of(skills);
    }

    public void setSkills(List<String> skills) {
        this.skills = skills == null ? new String[0] : skills.toArray(String[]::new);
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getSource() {
        return source;
    }

    public void setSource(String source) {
        this.source = source;
    }

    public String getExternalUrl() {
        return externalUrl;
    }

    public void setExternalUrl(String externalUrl) {
        this.externalUrl = externalUrl;
    }

    public OffsetDateTime getPostedAt() {
        return postedAt;
    }
}
