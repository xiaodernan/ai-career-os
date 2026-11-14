package com.careeros.application.dto;

import com.fasterxml.jackson.annotation.JsonAlias;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;

public final class ApplicationDtos {

    private ApplicationDtos() {
    }

    /**
     * One tracked application as the board reads it. `letters` is how many cover letters are kept
     * for it (53.2): the card needs the number without spending a request per card, so the list
     * route reads a page of totals in one grouped query. It is derived, never written here.
     */
    public record ApplicationItem(UUID id, UUID jobId, UUID companyId, String title,
                                  String companyName, String status, int position, String notes,
                                  OffsetDateTime reminderAt, UUID resumeVersionId, UUID jdId,
                                  UUID matchId, OffsetDateTime appliedAt, OffsetDateTime createdAt,
                                  OffsetDateTime updatedAt, String offerCompensation,
                                  String rejectionReason, int letters) {
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

    /**
     * One letter from the shelf the reader keeps across their applications — the same row
     * {@code /letters} lists, with the titles of the application it hangs off. The application
     * travels with the row because the gallery is the reader's ink desk, not a table of contents.
     * A letter whose application row is gone answers an empty title rather than a missing letter:
     * the letter is still theirs, and the title is where they would have started.
     */
    public record LetterCatalogItem(UUID id, UUID applicationId, String applicationTitle,
                                    String companyName, UUID jobId, UUID resumeVersionId,
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
     *
     * <p>`letters` is the fourth artifact and the only one that is a count: a kept letter is not a
     * column on the application but a row in its own table, and the reader may keep several.
     *
     * <p>`rehearsals` (57.2) is the fifth row and the second count: the mock interviews the reader
     * has run for this card. It is not part of the material that was sent, but it is what came
     * back -- and the row links to the narrowed interview list, so the count is a way in.
     */
    public record ApplicationPacket(UUID applicationId,
                                    boolean resumeLinked, PacketResume resume,
                                    boolean jdLinked, PacketJd jd,
                                    boolean matchLinked, PacketMatch match,
                                    int letters, int rehearsals,
                                    Float bestRehearsalScore) {
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
