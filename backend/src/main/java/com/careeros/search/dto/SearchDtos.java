package com.careeros.search.dto;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;

/** Global search results grouped by entity type; each group is capped. */
public final class SearchDtos {

    private SearchDtos() {
    }

    public record JobHit(UUID id, String title, String companyName, String location,
                         String remoteType, String status) {
    }

    public record CompanyHit(UUID id, String name, String industry, String website) {
    }

    public record ResumeHit(UUID id, String title, String status, OffsetDateTime updatedAt) {
    }

    public record NoteHit(UUID id, String title, String snippet, OffsetDateTime updatedAt) {
    }

    public record ConversationHit(UUID id, String title, String snippet, OffsetDateTime updatedAt) {
    }

    public record ApplicationHit(UUID id, String title, String companyName, String status,
                                 OffsetDateTime updatedAt) {
    }

    /**
     * A kept cover letter, found by its own words or by the posting it was written for. The
     * application id is what makes the hit actionable: the board's drawer opens on it (51.2).
     */
    public record LetterHit(UUID id, UUID applicationId, String jobTitle, String snippet,
                            OffsetDateTime updatedAt) {
    }

    public record SearchResponse(String query,
                                 List<JobHit> jobs,
                                 List<CompanyHit> companies,
                                 List<ResumeHit> resumes,
                                 List<NoteHit> notes,
                                 List<ConversationHit> conversations,
                                 List<ApplicationHit> applications,
                                 List<LetterHit> letters) {
    }
}
