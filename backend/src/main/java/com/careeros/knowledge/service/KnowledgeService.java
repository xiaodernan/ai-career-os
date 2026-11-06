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
import com.careeros.knowledge.dto.KnowledgeDtos.NoteTagCount;
import com.careeros.knowledge.dto.KnowledgeDtos.SourceItem;
import com.careeros.knowledge.dto.KnowledgeDtos.TextIngestResponse;
import com.careeros.knowledge.entity.Document;
import com.careeros.knowledge.entity.KnowledgeSource;
import com.careeros.knowledge.entity.UserNote;
import com.careeros.knowledge.repository.DocumentRepository;
import com.careeros.knowledge.repository.KnowledgeSourceRepository;
import com.careeros.knowledge.repository.UserNoteRepository;
import java.util.ArrayList;
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
    private final StoredObjectReclaimer reclaimer;

    public KnowledgeService(KnowledgeSourceRepository sources, DocumentRepository documents,
                            UserNoteRepository notes, FileIngestService fileIngest,
                            StoredObjectReclaimer reclaimer) {
        this.sources = sources;
        this.documents = documents;
        this.notes = notes;
        this.fileIngest = fileIngest;
        this.reclaimer = reclaimer;
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

    /**
     * Deleting a source retires its documents, drops the row and hands the retired keys to
     * {@link StoredObjectReclaimer}. The reclaim waits for this transaction's commit, so a delete
     * that rolls back never takes a file and a file another row still serves is never taken.
     */
    @Transactional
    public void deleteSource(UUID userId, UUID sourceId) {
        KnowledgeSource source = requireSource(userId, sourceId);
        List<String> retired = retireDocuments(userId, source);
        sources.delete(source);
        reclaimer.reclaim(retired);
    }

    /**
     * Drops the knowledge-base copy of a domain row that was deleted through its own page —
     * a resume removed from the resume list otherwise keeps a source row (a ghost entry the
     * user cannot open) and keeps feeding the AI.
     *
     * <p>The keys of what it retired come back to the caller, because the caller owns the
     * transaction that removes the domain row and only a reclaim after that commit sees whether
     * anything still names them. A caller that leaves the domain row alive — switching a resume to
     * another version retires that resume's copy while the resume itself keeps serving its
     * upload — has nothing to reclaim.
     */
    @Transactional
    public List<String> retireRef(UUID userId, String kind, UUID refId) {
        List<String> keys = new ArrayList<>();
        for (KnowledgeSource source : sources.findByUserIdAndKindAndRefId(userId, kind, refId)) {
            keys.addAll(retireDocuments(userId, source));
            sources.delete(source);
        }
        return keys;
    }

    /**
     * Retrieval admits a chunk only while its document row reads
     * {@code documents.status = 'ready'} — that single predicate is the gate all three hybrid
     * channels share. So un-owning a source leaves the deleted material fully quotable: the
     * row must stop being ready. The document and its chunks stay as the audit record the original
     * un-linking was written to preserve, and the row keeps naming its file key so that record can
     * still be traced back to what was stored; the object itself is the caller's to reclaim.
     */
    private List<String> retireDocuments(UUID userId, KnowledgeSource source) {
        // Both directions of the link are covered: ingestion writes documents.source_id,
        // while the ready callback only knows knowledge_sources.document_id.
        Set<Document> docs = new LinkedHashSet<>(documents.findBySourceId(source.getId()));
        if (source.getDocumentId() != null) {
            documents.findByIdAndUserId(source.getDocumentId(), userId).ifPresent(docs::add);
        }
        List<String> keys = new ArrayList<>();
        for (Document doc : docs) {
            doc.setSourceId(null);
            doc.setStatus(STATUS_RETIRED);
            if (doc.getFileKey() != null) {
                keys.add(doc.getFileKey());
            }
        }
        documents.saveAll(docs);
        return keys;
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

    /**
     * 64.2: the notes list can be asked for one tag. The report's advice carries
     * its own tags (study, answer, gap, prepare), so this is how the knowledge
     * page singles out "the advice a rehearsal left" from everything else. A
     * blank tag is not a filter -- it is the whole list, in the order it always had.
     */
    @Transactional(readOnly = true)
    public PageDTO<NoteItem> listNotes(UUID userId, int page, int size, String tag) {
        var pageable = Paging.of(page, size).pageable();
        String filter = tag == null ? "" : tag.trim();
        var result = filter.isEmpty()
                ? notes.findByUserIdOrderByUpdatedAtDescIdAsc(userId, pageable)
                : notes.findByTag(userId, filter, pageable);
        return PageDTO.from(result, KnowledgeService::toNoteItem);
    }

    /**
     * 69.2: the reader's own tag vocabulary with its counts. Ordered by the count
     * descending and then by the label, so the tag with the most behind it is the
     * first thing the filter row offers -- and two tags with the same count keep a
     * stable order instead of following whatever the planner returned.
     */
    @Transactional(readOnly = true)
    public List<NoteTagCount> noteTagCounts(UUID userId) {
        return notes.countByTag(userId).stream()
                .map(row -> new NoteTagCount(row.getTag(), row.getTotal()))
                .toList();
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
        // The retired copy's key is not reclaimed: this note survives the call,
        // the way a resume survives switching its current version does.
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
        List<String> retired = retireRef(userId, "note", note.getId());
        notes.delete(note);
        reclaimer.reclaim(retired);
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
