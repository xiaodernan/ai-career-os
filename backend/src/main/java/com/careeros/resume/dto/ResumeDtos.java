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

    public record ResumeVersionItem(UUID id, UUID resumeId, String label, String kind, UUID jobId,
                                    OffsetDateTime createdAt) {
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

    public record UploadResumeResponse(UUID resumeId, UUID versionId, UUID documentId,
                                       UUID sourceId, UUID taskId) {
    }

    public record ParseResumeResponse(UUID resumeId, UUID versionId, Map<String, Object> score,
                                      int experiences, int projects, int educations,
                                      int achievements, int skills) {
    }
}
