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
                                  OffsetDateTime updatedAt, String offerCompensation,
                                  String rejectionReason) {
    }

    /** The resume version this application carries, resolved for a reader rather than an id. */
    public record PacketResume(UUID id, UUID resumeId, String title, String label, String kind,
                               OffsetDateTime createdAt) {
    }

    /**
     * The JD analysis this application carries. `title` and `companyName` are the analyst's own
     * reading when it named them, and the posting's when it did not; `jobId` is the posting the
     * analysis belongs to, and is null for a pasted JD that was never attached to one.
     */
    public record PacketJd(UUID id, UUID jobId, String title, String companyName,
                           OffsetDateTime createdAt) {
    }

    public record PacketMatch(UUID id, UUID jobId, float overall, OffsetDateTime createdAt) {
    }

    /**
     * One cover letter kept for an application. The mode, tone and length are the dials the
     * writer was asked with -- null when the draft came from a path that did not ask -- and the
     * body is the letter itself, kept whole because that is the thing the reader wanted.
     */
    public record LetterItem(UUID id, UUID applicationId, UUID jobId, UUID resumeVersionId,
                             String mode, String tone, String length, String body,
                             OffsetDateTime createdAt, OffsetDateTime updatedAt) {
    }

    /** A draft the reader chose to keep; the application row supplies the posting and version. */
    public record SaveLetterRequest(@JsonAlias("resume_version_id") UUID resumeVersionId,
                                    String mode, String tone, String length,
                                    @NotBlank @Size(max = 20000) String body) {
    }

    /**
     * The correction of a kept letter. The body is the one required component -- a letter
     * without text is not a letter -- while a null dial leaves the stored value alone and an
     * empty one clears it, the same null-versus-empty rule the application PATCH follows.
     */
    public record UpdateLetterRequest(@NotBlank @Size(max = 20000) String body,
                                      String mode, String tone, String length) {
    }

    /**
     * What one tracked application carries from the pipeline.
     *
     * <p>The three `*Linked` flags are read from the application's own columns; the value beside
     * each is null when that column is empty <em>or</em> when the row it names is not the caller's.
     * A reader can therefore tell "nothing was ever linked" from "the thing that was linked can no
     * longer be read", without this route revealing whether an id belongs to another account.
     */
    public record ApplicationPacket(UUID applicationId,
                                    boolean resumeLinked, PacketResume resume,
                                    boolean jdLinked, PacketJd jd,
                                    boolean matchLinked, PacketMatch match) {
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

    /**
     * The PATCH body. A null component means "leave it alone", which is why clearing the
     * reminder needs its own flag: Jackson cannot tell an absent field from an explicit null.
     * {@code reminderAt} wins when a caller sends both.
     */
    public record UpdateApplicationRequest(String status,
                                           Integer position,
                                           String note,
                                           @JsonAlias("reminder_at") OffsetDateTime reminderAt,
                                           @JsonAlias("clear_reminder_at") Boolean clearReminderAt,
                                           @JsonAlias("offer_compensation") String offerCompensation,
                                           @JsonAlias("rejection_reason") String rejectionReason) {
    }

    public record ReorderRequest(int position, String status) {
    }

    public record TimelineEvent(UUID id, String kind, Map<String, Object> payload,
                                OffsetDateTime createdAt) {
    }
}
