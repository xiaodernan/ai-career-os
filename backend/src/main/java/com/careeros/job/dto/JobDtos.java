package com.careeros.job.dto;

import com.fasterxml.jackson.annotation.JsonAlias;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;

public final class JobDtos {

    private JobDtos() {
    }

    public record JobListItem(UUID id, String title, UUID companyId, String companyName,
                              String location, String remoteType, String employmentType,
                              Integer salaryMin, Integer salaryMax, String salaryCurrency,
                              Integer experienceYears, String status, String source,
                              String externalUrl, OffsetDateTime postedAt, List<String> skills,
                              Float matchOverall, UUID matchId) {
    }

    public record JobDetail(UUID id, String title, UUID companyId, CompanyItem company,
                            String location, String remoteType, String employmentType,
                            Integer salaryMin, Integer salaryMax, String salaryCurrency,
                            Integer experienceYears, String description, List<String> requirements,
                            List<String> niceToHave, List<String> responsibilities,
                            List<String> skills, String status, String source, String externalUrl,
                            OffsetDateTime postedAt, MatchSummary match, JdItem jd, boolean saved) {
    }

    public record MatchSummary(UUID id, float overall, float technical, float experience,
                               float projects, float education, List<Object> matchedSkills,
                               List<Object> missingSkills, List<Object> evidence,
                               String narrative, OffsetDateTime createdAt) {
    }

    public record JdItem(UUID id, UUID jobId, String rawText, Map<String, Object> parsed,
                         OffsetDateTime createdAt) {
    }

    public record CompanyItem(UUID id, String name, String website, String logoUrl,
                              String industry, String size, String overview,
                              List<String> techStack, long openRoles) {
    }

    public record CompanyRequest(@NotBlank @Size(max = 200) String name, String website,
                                 String logoUrl, String industry, String size, String overview,
                                 List<String> techStack, String culture, String interviewProcess,
                                 List<Object> sources) {
    }

    public record CreateJobRequest(@NotBlank @Size(max = 300) String title,
                                   @JsonAlias("company_id") UUID companyId,
                                   CompanyRequest company,
                                   String location,
                                   @JsonAlias("remote_type") String remoteType,
                                   @JsonAlias("employment_type") String employmentType,
                                   @JsonAlias("salary_min") Integer salaryMin,
                                   @JsonAlias("salary_max") Integer salaryMax,
                                   @JsonAlias("salary_currency") String salaryCurrency,
                                   @JsonAlias("experience_years") Integer experienceYears,
                                   @NotBlank String description,
                                   List<String> requirements,
                                   @JsonAlias("nice_to_have") List<String> niceToHave,
                                   List<String> responsibilities,
                                   List<String> skills,
                                   String status,
                                   @JsonAlias("external_url") String externalUrl) {
    }

    public record ImportJobRequest(@NotBlank @JsonAlias({"raw_text", "rawText"}) String rawText,
                                   String url) {
    }

    public record SaveJobRequest(String note) {
    }

    public record SavedJobItem(JobListItem job, String note, OffsetDateTime savedAt) {
    }

    public record MatchRequest(@JsonAlias("resume_version_id") UUID resumeVersionId) {
    }

    public record MatchResponse(Map<String, Object> match, UUID matchId, Map<String, Object> jd) {
    }

    public record JdRequest(@NotBlank @JsonAlias("raw_text") String rawText,
                            @JsonAlias("job_id") UUID jobId) {
    }

    public record JdSuggestionsRequest(@JsonAlias("resume_version_id") UUID resumeVersionId,
                                       @NotBlank @JsonAlias("jd_raw") String jdRaw) {
    }

    public record TailorRequest(@JsonAlias("resume_version_id") UUID resumeVersionId) {
    }

    public record TailorResponse(UUID versionId, Map<String, Object> tailored,
                                 Map<String, Object> diff, List<Object> notes,
                                 List<Object> evidence, Map<String, Object> stats) {
    }

    public record CoverLetterRequest(@JsonAlias("resume_version_id") UUID resumeVersionId,
                                     String mode, String previous, String goal,
                                     String tone, String length) {
    }
}
