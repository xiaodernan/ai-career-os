package com.careeros.knowledge.service;

import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.common.Json;
import com.careeros.common.PageDTO;
import com.careeros.common.Paging;
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
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.Map;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

/** Career knowledge base: sources + documents + notes. */
@Service
public class KnowledgeService {

    private static final List<String> KINDS = List.of("resume", "project", "note", "jd", "company",
            "interview_feedback", "certificate", "course", "goal");

    /** Terminal, non-retrievable document status set when the owning row is deleted. */
    private static final String STATUS_RETIRED = "retired";

    private static final Logger log = LoggerFactory.getLogger(KnowledgeService.class);

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
    public PageDTO<SourceItem> listSources(UUID userId, int page, int size, UUID documentId) {
        var paging = Paging.of(page, size);
        var result = documentId == null
                ? sources.findByUserIdOrderByCreatedAtDescIdAsc(userId, paging.pageable())
                : sources.findByUserIdAndDocumentIdOrderByCreatedAtDescIdAsc(userId, documentId,
                        paging.pageable());
        return PageDTO.from(result, SourceItem::from);
    }

    @Transactional
    public void deleteSource(UUID userId, UUID sourceId) {
        KnowledgeSource source = requireSource(userId, sourceId);
        retireDocuments(userId, source);
        sources.delete(source);
    }

    /**
     * Drops the knowledge-base copy of a domain row that was deleted through its own page —
     * a resume removed from the resume list otherwise keeps a source row (a ghost entry the
     * user cannot open) and keeps feeding the AI.
     */
    @Transactional
    public void retireRef(UUID userId, String kind, UUID refId) {
        for (KnowledgeSource source : sources.findByUserIdAndKindAndRefId(userId, kind, refId)) {
            retireDocuments(userId, source);
            sources.delete(source);
        }
    }

    /**
     * Retrieval admits a chunk only while its document row reads
     * {@code documents.status = 'ready'} — that single predicate is the gate all three hybrid
     * channels share. So un-owning a source leaves the deleted material fully quotable: the
     * row must stop being ready. The document and its chunks stay on disk as the audit record
     * the original un-linking was written to preserve; the object-storage file is untouched.
     */
    private void retireDocuments(UUID userId, KnowledgeSource source) {
        // Both directions of the link are covered: ingestion writes documents.source_id,
        // while the ready callback only knows knowledge_sources.document_id.
        Set<Document> docs = new LinkedHashSet<>(documents.findBySourceId(source.getId()));
        if (source.getDocumentId() != null) {
            documents.findByIdAndUserId(source.getDocumentId(), userId).ifPresent(docs::add);
        }
        for (Document doc : docs) {
            doc.setSourceId(null);
            doc.setStatus(STATUS_RETIRED);
        }
        documents.saveAll(docs);
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
        var result = notes.findByUserIdOrderByUpdatedAtDescIdAsc(userId, Paging.of(page, size).pageable());
        return PageDTO.from(result, KnowledgeService::toNoteItem);
    }

    @Transactional
    public NoteItem createNote(UUID userId, NoteRequest request) {
        UserNote note = new UserNote();
        note.setUserId(userId);
        note.setTitle(request.title() == null ? "" : request.title());
        note.setContent(request.content());
        note.setTags(request.tags());
        // Flushed, not just saved: the id is the database's to mint, and the
        // ingested copy has to carry it -- it is what the delete path
        // retires, and a copy with no reference would be a copy nothing can
        // take back.
        notes.saveAndFlush(note);
        // A note is a *citable* note: the panel promises the agents can quote it
        // back, and retrieval admits a chunk only while its document row reads
        // 'ready' -- so the text has to be ingested, or the promise is about a
        // row the reader's own words never reach. The kind is "note" and the
        // reference is the note's own id, which is what deleting the note
        // retires (see deleteNote) and what un-linking a domain row retires.
        ingestNote(userId, note);
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
        // The note's text changed, so the chunks that carry the old text have
        // to go: the reader deleted a sentence and the assistant keeps
        // quoting it. Retiring them is what leaves the *old* document
        // unquotable, and the fresh ingest is what carries the new text.
        retireRef(userId, "note", note.getId());
        ingestNote(userId, note);
        return toNoteItem(note);
    }

    /**
     * Ingest a note's text so the agents can quote it.
     *
     * <p>The note's own id is the reference, the way a resume's is: it is what
     * ties the ingested copy to the row the reader wrote and edits, and what
     * lets the delete path retire exactly this copy.
     */
    private void ingestNote(UUID userId, UserNote note) {
        String text = note.getContent();
        if (text == null || text.isBlank()) {
            return;
        }
        try {
            fileIngest.ingestText(userId, note.getTitle(), text, "note", note.getId());
        } catch (RuntimeException e) {
            // The note is written either way -- the reader asked for a note and
            // the note is theirs. What failed is the copy the agents quote, and
            // the next edit or delete will try again.
            log.warn("Ingesting the note failed for user {}: {}", userId, e.getMessage());
        }
    }

    @Transactional
    public void deleteNote(UUID userId, UUID noteId) {
        UserNote note = requireNote(userId, noteId);
        // Same rule as a deleted resume: the note was embedded, so dropping the row while its
        // chunks stay 'ready' leaves the AI quoting text the user just deleted.
        retireRef(userId, "note", note.getId());
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
            throw new ApiException(ApiErrorCode.UPLOAD_UNREADABLE, "Cannot read upload");
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
            throw new ApiException(ApiErrorCode.VALIDATION_KIND_UNKNOWN, "Unknown knowledge kind: " + kind);
        }
    }

    static NoteItem toNoteItem(UserNote n) {
        return new NoteItem(n.getId(), n.getTitle(), n.getContent(), n.getTags(), n.getCreatedAt(),
                n.getUpdatedAt());
    }
}
