package com.careeros.knowledge.dto;

import com.careeros.knowledge.entity.KnowledgeSource;
import com.fasterxml.jackson.annotation.JsonAlias;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;

public final class KnowledgeDtos {

    private KnowledgeDtos() {
    }

    public record SourceItem(UUID id, String kind, UUID refId, String title, String status,
                             String error, UUID documentId, OffsetDateTime createdAt) {

        public static SourceItem from(KnowledgeSource s) {
            return new SourceItem(s.getId(), s.getKind(), s.getRefId(), s.getTitle(), s.getStatus(),
                    s.getError(), s.getDocumentId(), s.getCreatedAt());
        }
    }

    public record NoteItem(UUID id, String title, String content, List<String> tags,
                           OffsetDateTime createdAt, OffsetDateTime updatedAt) {
    }

    public record NoteRequest(@Size(max = 200) String title, @NotBlank String content,
                              List<String> tags) {
    }

    public record TextIngestRequest(@Size(max = 200) String title, @NotBlank String text,
                                    @NotBlank String kind, @JsonAlias("ref_id") UUID refId) {
    }

    public record TextIngestResponse(UUID taskId, UUID documentId, UUID sourceId) {
    }

    public record DocumentStatus(UUID documentId, String status, String error, String title) {
    }

    public record IngestResultDto(UUID taskId, UUID documentId, UUID sourceId) {
    }
}
