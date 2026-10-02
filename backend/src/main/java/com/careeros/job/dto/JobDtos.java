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
                               List<Object> whyMatch, List<Object> preparation,
                               List<Object> skillGaps,
                               String narrative, OffsetDateTime createdAt) {
    }

    public record JdItem(UUID id, UUID jobId, String rawText, Map<String, Object> parsed,
                         OffsetDateTime createdAt) {
    }

    /**
     * One company as the list, the job detail and the company page send it.
     *
     * <p>{@code culture}, {@code interviewProcess} and {@code sources} were write-only until the
     * company page needed them: {@code CompanyRequest} has accepted all three since the first
     * migration, the {@code companies} row stores them, and no read path ever carried them back —
     * so a researched profile could be posted and then never seen again.
     *
     * <p>The count is named {@code openRoleCount} rather than {@code openRoles} so it cannot be
     * mistaken for the list of roles beside it on {@link CompanyDetail}: the two were one name, and
     * the browser read the number as a list.
     */
    public record CompanyItem(UUID id, String name, String website, String logoUrl,
                              String industry, String size, String overview,
                              List<String> techStack, String culture, String interviewProcess,
                              List<Object> sources, long openRoleCount) {
    }

    /**
     * {@code GET /api/v1/companies/{id}}: the profile, plus the roles the company is hiring for.
     *
     * <p>The roles are the board's own rows — same columns, same latest-match lateral join, same
     * {@code match} ordering — scoped to this company and to {@code status = 'open'}, which is the
     * predicate {@link CompanyItem#openRoleCount()} counts. Two definitions of "open" is how a count
     * and the list under it end up disagreeing on screen.
     */
    public record CompanyDetail(CompanyItem company, List<JobListItem> openRoles) {
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

    public record CoverLetterRequest(@JsonAlias("resume_version_id") UUID resumeVersionId,
                                     String mode, String previous, String goal,
                                     String tone, String length) {
    }
}
