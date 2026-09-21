package com.careeros.knowledge.service;

import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.common.Json;
import com.careeros.common.PageDTO;
import com.careeros.knowledge.dto.KnowledgeDtos.DocumentStatus;
import com.careeros.knowledge.dto.KnowledgeDtos.IngestResultDto;
import com.careeros.knowledge.dto.KnowledgeDtos.NoteItem;
import com.careeros.knowledge.dto.KnowledgeDtos.NoteRequest;
import com.careeros.knowledge.dto.KnowledgeDtos.SourceItem;
import com.careeros.knowledge.dto.KnowledgeDtos.TextIngestResponse;
import com.careeros.knowledge.entity.Document;
import com.careeros.knowledge.entity.KnowledgeSource;
import com.careeros.knowledge.entity.UserNote;
import com.careeros.knowledge.repository.DocumentRepository;
import com.careeros.knowledge.repository.KnowledgeSourceRepository;
import com.careeros.knowledge.repository.UserNoteRepository;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

/** Career knowledge base: sources + documents + notes. */
@Service
public class KnowledgeService {

    private static final List<String> KINDS = List.of("resume", "project", "note", "jd", "company",
            "interview_feedback", "certificate", "course", "goal");

    private final KnowledgeSourceRepository sources;
    private final DocumentRepository documents;
    private final UserNoteRepository notes;
    private final FileIngestService fileIngest;

    public KnowledgeService(KnowledgeSourceRepository sources, DocumentRepository documents,
                            UserNoteRepository notes, FileIngestService fileIngest) {
        this.sources = sources;
        this.documents = documents;
        this.notes = notes;
        this.fileIngest = fileIngest;
    }

    @Transactional(readOnly = true)
    public PageDTO<SourceItem> listSources(UUID userId, int page, int size) {
        var result = sources.findByUserIdOrderByCreatedAtDesc(userId, PageRequest.of(page, size));
        return PageDTO.from(result, SourceItem::from);
    }

    @Transactional
    public void deleteSource(UUID userId, UUID sourceId) {
        KnowledgeSource source = requireSource(userId, sourceId);
        List<Document> docs = documents.findBySourceId(sourceId);
        for (Document doc : docs) {
            doc.setSourceId(null); // un-own: chunks cascade with the document, files stay for audit
        }
        documents.saveAll(docs);
        sources.delete(source);
    }

    @Transactional(readOnly = true)
    public DocumentStatus sourceStatus(UUID userId, UUID sourceId) {
        KnowledgeSource source = requireSource(userId, sourceId);
        Document doc = source.getDocumentId() == null ? null
                : documents.findById(source.getDocumentId()).orElse(null);
        if (doc == null) {
            return new DocumentStatus(source.getDocumentId(), source.getStatus(), source.getError(),
                    source.getTitle());
        }
        return new DocumentStatus(doc.getId(), doc.getStatus(), doc.getError(), doc.getTitle());
    }

    @Transactional(readOnly = true)
    public PageDTO<NoteItem> listNotes(UUID userId, int page, int size) {
        var result = notes.findByUserIdOrderByUpdatedAtDesc(userId, PageRequest.of(page, size));
        return PageDTO.from(result, KnowledgeService::toNoteItem);
    }

    @Transactional
    public NoteItem createNote(UUID userId, NoteRequest request) {
        UserNote note = new UserNote();
        note.setUserId(userId);
        note.setTitle(request.title() == null ? "" : request.title());
        note.setContent(request.content());
        note.setTags(request.tags());
        notes.save(note);
        return toNoteItem(note);
    }

    @Transactional
    public NoteItem updateNote(UUID userId, UUID noteId, NoteRequest request) {
        UserNote note = requireNote(userId, noteId);
        if (request.title() != null) {
            note.setTitle(request.title());
        }
        if (request.content() != null) {
            note.setContent(request.content());
        }
        if (request.tags() != null) {
            note.setTags(request.tags());
        }
        notes.save(note);
        return toNoteItem(note);
    }

    @Transactional
    public void deleteNote(UUID userId, UUID noteId) {
        UserNote note = requireNote(userId, noteId);
        sources.findFirstByUserIdAndKindAndRefId(userId, "note", note.getId())
                .ifPresent(s -> s.setRefId(null));
        notes.delete(note);
    }

    public TextIngestResponse ingestText(UUID userId, String title, String text, String kind, UUID refId) {
        validateKind(kind);
        Map<String, Object> result = fileIngest.ingestText(userId, title, text, kind, refId);
        return new TextIngestResponse(Json.uuidOrNull(result, "task_id"),
                Json.uuidOrNull(result, "document_id"), Json.uuidOrNull(result, "source_id"));
    }

    public IngestResultDto uploadDocument(UUID userId, MultipartFile file, String kind, String title) {
        String effectiveKind = kind == null || kind.isBlank() ? "note" : kind;
        validateKind(effectiveKind);
        byte[] content;
        try {
            content = file.getBytes();
        } catch (java.io.IOException e) {
            throw new ApiException(ApiErrorCode.BAD_REQUEST, "Cannot read upload");
        }
        String folder = "knowledge";
        FileIngestService.Persisted persisted =
                fileIngest.persistRowsOnly(userId, content, title, effectiveKind, folder);
        try {
            Map<String, Object> result = fileIngest.triggerIngest(persisted, userId);
            return new IngestResultDto(Json.uuidOrNull(result, "task_id"), persisted.documentId(),
                    persisted.sourceId());
        } catch (ApiException e) {
            fileIngest.markFailed(persisted, "ingestion trigger failed");
            throw e;
        }
    }

    public KnowledgeSource requireSource(UUID userId, UUID sourceId) {
        return sources.findByIdAndUserId(sourceId, userId)
                .orElseThrow(() -> new ApiException(ApiErrorCode.SOURCE_NOT_FOUND, "Knowledge source not found"));
    }

    private UserNote requireNote(UUID userId, UUID noteId) {
        return notes.findByIdAndUserId(noteId, userId)
                .orElseThrow(() -> new ApiException(ApiErrorCode.NOTE_NOT_FOUND, "Note not found"));
    }

    private static void validateKind(String kind) {
        if (!KINDS.contains(kind)) {
            throw new ApiException(ApiErrorCode.VALIDATION_FAILED, "Unknown knowledge kind: " + kind);
        }
    }

    static NoteItem toNoteItem(UserNote n) {
        return new NoteItem(n.getId(), n.getTitle(), n.getContent(), n.getTags(), n.getCreatedAt(),
                n.getUpdatedAt());
    }
}
