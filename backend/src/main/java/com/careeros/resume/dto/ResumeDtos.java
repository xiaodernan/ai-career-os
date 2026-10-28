package com.careeros.resume.dto;

import com.careeros.resume.entity.Resume;
import com.fasterxml.jackson.annotation.JsonAlias;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;

public final class ResumeDtos {

    private ResumeDtos() {
    }

    public record ResumeListItem(UUID id, String title, String status, UUID currentVersionId,
                                 OffsetDateTime createdAt) {

        public static ResumeListItem from(Resume r) {
            return new ResumeListItem(r.getId(), r.getTitle(), r.getStatus(),
                    r.getCurrentVersionId(), r.getCreatedAt());
        }
    }

    /**
     * `diff` is the tailor change list that produced this version, so the version list can show
     * what a draft actually changed. `structured` stays out: it is the whole resume body per row.
     */
    /**
     * `score` is the same rubric map `ResumeDetail.score` carries -- the jsonb the parsing run
     * persisted for this version. The versions panel shows one score per version, so a row without
     * the column would answer "never scored" for versions that were (#134 gave the list the field
     * its own UI had been reading since the panel was wired). Null only for a version that has
     * never been parsed, such as a fresh tailored copy.
     */
    public record ResumeVersionItem(UUID id, UUID resumeId, String label, String kind, UUID jobId,
                                    OffsetDateTime createdAt, Map<String, Object> diff,
                                    Map<String, Object> score) {
    }

    /**
     * 19.5 -- the print view's request. The document is written in the reader's
     * language, so the request carries it; the version is in the path, and
     * everything else the renderer needs is the version's own.
     */
    public record PrintResumeRequest(@Size(max = 16) String locale) {
    }

    /**
     * The print-ready document for one version: self-contained HTML, so the
     * browser's own print dialog is the PDF. It is a record rather than a raw
     * string because the envelope carries a `data` object, not a document.
     */
    public record ResumePrint(String html) {
    }

    public record ExperienceItem(UUID id, String company, String title, String startDate,
                                 String endDate, String location, List<String> bullets,
                                 String summary, int ordinal) {
    }

    public record ProjectItem(UUID id, String name, String role, String period,
                              List<String> bullets, List<String> tech, String url, int ordinal) {
    }

    public record EducationItem(UUID id, String school, String degree, String field,
                                Integer startYear, Integer endYear, String gpa,
                                List<String> courses, int ordinal) {
    }

    public record AchievementItem(UUID id, String text, int ordinal) {
    }

    public record SkillItem(UUID id, String name, String category, Float proficiency) {
    }

    public record ResumeDetail(UUID id, String title, String status, String sourceFileKey,
                               UUID currentVersionId, OffsetDateTime createdAt,
                               Map<String, Object> structured,
                               String plaintext, Map<String, Object> score,
                               List<ExperienceItem> experiences, List<ProjectItem> projects,
                               List<EducationItem> educations, List<AchievementItem> achievements,
                               List<SkillItem> skills) {
    }

    /**
     * The resume body is `plaintext`. The extra aliases matter because Jackson
     * silently ignores unknown properties: a client sending `rawText` would get a
     * 201 with an empty, unparseable resume instead of an error. Accepting the
     * obvious spellings turns that silent data loss into a working request.
     */
    public record CreateResumeRequest(@NotBlank @Size(max = 200) String title,
                                      @JsonAlias({"plaintext", "plain_text", "rawText", "raw_text",
                                              "text"}) String plaintext) {
    }

    public record UpdateResumeRequest(@Size(min = 1, max = 200) String title) {
    }

    public record SetCurrentVersionRequest(@JsonAlias({"version_id"}) UUID versionId) {
    }

    /**
     * A tailored draft the user decided to keep. `tailored` is the structured body exactly as
     * the AI returned it, `diff` the accepted/rejected change list, `plaintext` the assembled
     * document. `resumeVersionId` names the version the draft was generated from; leave it out
     * and the server applies the same "current resume" rule the tailor call itself used, so the
     * version lands on the resume the draft came from.
     */
    public record TailoredVersionRequest(@JsonAlias("resume_version_id") UUID resumeVersionId,
                                         Map<String, Object> tailored,
                                         Map<String, Object> diff,
                                         @JsonAlias({"plain_text", "markdown"}) String plaintext) {
    }

    public record UploadResumeResponse(UUID resumeId, UUID versionId, UUID documentId,
                                       UUID sourceId, UUID taskId) {
    }

    public record ParseResumeResponse(UUID resumeId, UUID versionId, Map<String, Object> score,
                                      int experiences, int projects, int educations,
                                      int achievements, int skills) {
    }
}
