package com.careeros.application.dto;

import com.fasterxml.jackson.annotation.JsonAlias;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import java.time.OffsetDateTime;
import java.util.Map;
import java.util.UUID;

public final class ApplicationDtos {

    private ApplicationDtos() {
    }

    public record ApplicationItem(UUID id, UUID jobId, UUID companyId, String title,
                                  String companyName, String status, int position, String notes,
                                  OffsetDateTime reminderAt, UUID resumeVersionId, UUID jdId,
                                  UUID matchId, OffsetDateTime appliedAt, OffsetDateTime createdAt,
                                  OffsetDateTime updatedAt) {
    }

    public record CreateApplicationRequest(@JsonAlias("job_id") UUID jobId,
                                           @JsonAlias("company_id") UUID companyId,
                                           @NotBlank @Size(max = 300) String title,
                                           @JsonAlias("company_name") String companyName,
                                           String status,
                                           @JsonAlias("resume_version_id") UUID resumeVersionId,
                                           @JsonAlias("jd_id") UUID jdId,
                                           @JsonAlias("match_id") UUID matchId,
                                           String notes,
                                           @JsonAlias("reminder_at") OffsetDateTime reminderAt) {
    }

    public record UpdateApplicationRequest(String status,
                                           Integer position,
                                           String note,
                                           @JsonAlias("reminder_at") OffsetDateTime reminderAt) {
    }

    public record ReorderRequest(int position, String status) {
    }

    public record TimelineEvent(UUID id, String kind, Map<String, Object> payload,
                                OffsetDateTime createdAt) {
    }
}
