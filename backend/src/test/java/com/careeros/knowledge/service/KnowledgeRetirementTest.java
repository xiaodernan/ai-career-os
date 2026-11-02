package com.careeros.knowledge.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.knowledge.entity.Document;
import com.careeros.knowledge.entity.KnowledgeSource;
import com.careeros.knowledge.entity.UserNote;
import com.careeros.knowledge.repository.DocumentRepository;
import com.careeros.knowledge.repository.KnowledgeSourceRepository;
import com.careeros.knowledge.repository.UserNoteRepository;
import java.util.List;
import java.util.Optional;
import static org.mockito.Mockito.when;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/**
 * Deleting knowledge must stop the AI retrieving it. All three hybrid search channels admit a
 * chunk only while its document row reads status = 'ready', so un-owning a source leaves the
 * deleted text fully quotable as evidence.
 *
 * <p>The second half of a delete is what the row was the only pointer to: an upload's bytes.
 * Retirement hands the key to {@link StoredObjectReclaimer} once the rows commit, and only for a
 * delete that can end the key's whole life — so this file also pins which delete asks the question
 * and which one does not.
 */
class KnowledgeRetirementTest {

    /** The key an upload stores its bytes under, as the delete path finds it on the document row. */
    private static final String FILE_KEY = "a-user/uploads/a-blob.bin";

    private final UUID userId = UUID.randomUUID();
    private final UUID sourceId = UUID.randomUUID();
    private final UUID documentId = UUID.randomUUID();
    private final UUID resumeId = UUID.randomUUID();
    private final UUID noteId = UUID.randomUUID();

    private KnowledgeSourceRepository sources;
    private DocumentRepository documents;
    private UserNoteRepository notes;
    private StoredObjectReclaimer reclaimer;
    private KnowledgeService service;

    @BeforeEach
    void setUp() {
        sources = mock(KnowledgeSourceRepository.class);
        documents = mock(DocumentRepository.class);
        notes = mock(UserNoteRepository.class);
        reclaimer = mock(StoredObjectReclaimer.class);
        service = new KnowledgeService(sources, documents, notes, mock(FileIngestService.class),
                reclaimer);
    }

    private KnowledgeSource source() {
        KnowledgeSource source = new KnowledgeSource();
        source.setUserId(userId);
        source.setKind("resume");
        source.setRefId(resumeId);
        source.setDocumentId(documentId);
        source.setStatus("ready");
        when(sources.findByIdAndUserId(sourceId, userId)).thenReturn(Optional.of(source));
        return source;
    }

    private Document document() {
        return document(FILE_KEY);
    }

    /** An inline-text copy has no key at all: nothing was stored, so there is nothing to reclaim. */
    private Document textDocument() {
        return document(null);
    }

    private Document document(String fileKey) {
        Document doc = new Document();
        doc.setUserId(userId);
        doc.setSourceId(sourceId);
        doc.setFileKey(fileKey);
        doc.setStatus("ready");
        when(documents.findByIdAndUserId(documentId, userId)).thenReturn(Optional.of(doc));
        return doc;
    }

    @Test
    void deletingASourceTakesItsChunksOutOfRetrieval() {
        KnowledgeSource source = source();
        Document doc = document();
        when(documents.findBySourceId(any())).thenReturn(List.of(doc));

        service.deleteSource(userId, sourceId);

        // 'ready' is the gate every retrieval channel shares; leave it and the text keeps
        // being quoted as evidence after the user deleted it.
        assertThat(doc.getStatus()).isNotEqualTo("ready");
        assertThat(doc.getStatus()).isEqualTo("retired");
        assertThat(doc.getSourceId()).isNull();
        verify(documents).saveAll(any());
        verify(sources).delete(source);
        // The upload's bytes are the other half of what the reader deleted, and this is the delete
        // that can end them: the source row was the only thing naming the key.
        verify(reclaimer).reclaim(List.of(FILE_KEY));
    }

    @Test
    void deletingASourceWhoseCopyWasInlineTextReclaimsNoObject() {
        source();
        Document doc = textDocument();
        when(documents.findBySourceId(any())).thenReturn(List.of(doc));

        service.deleteSource(userId, sourceId);

        assertThat(doc.getStatus()).isEqualTo("retired");
        // Nothing was stored, so there is no key to judge: the reclaimer is asked about nothing
        // rather than about a null that would read as a key.
        verify(reclaimer).reclaim(List.of());
    }

    @Test
    void deletingTheDomainRowRetiresTheIngestedCopyToo() {
        KnowledgeSource source = source();
        Document doc = document();
        when(documents.findBySourceId(any())).thenReturn(List.of());
        when(sources.findByUserIdAndKindAndRefId(userId, "resume", resumeId))
                .thenReturn(List.of(source));

        List<String> keys = service.retireRef(userId, "resume", resumeId);

        // retirement has to work through knowledge_sources.document_id alone — that is the
        // link the ingest callback sets, and the resume path relies on it.
        assertThat(doc.getStatus()).isEqualTo("retired");
        verify(sources).delete(source);
        // and the key it found comes back to the caller, which is the one that knows whether the
        // row it is also deleting ends the key's life.
        assertThat(keys).containsExactly(FILE_KEY);
    }

    @Test
    void theSameDocumentReachedByBothLinksIsRetiredOnce() {
        KnowledgeSource source = source();
        Document doc = document();
        when(documents.findBySourceId(any())).thenReturn(List.of(doc));
        when(sources.findByUserIdAndKindAndRefId(userId, "resume", resumeId))
                .thenReturn(List.of(source));

        List<String> keys = service.retireRef(userId, "resume", resumeId);

        assertThat(doc.getStatus()).isEqualTo("retired");
        verify(sources).delete(source);
        // One document, one key: found through both links, judged for reclamation once.
        assertThat(keys).containsExactly(FILE_KEY);
    }

    @Test
    void deletingANoteRetiresItsEmbeddedCopy() {
        KnowledgeSource source = source();
        Document doc = textDocument();
        when(documents.findBySourceId(any())).thenReturn(List.of(doc));
        // UserNote's id is assigned by the database, so the entity is mocked to carry one.
        UserNote note = mock(UserNote.class);
        when(note.getId()).thenReturn(noteId);
        when(notes.findByIdAndUserId(noteId, userId)).thenReturn(Optional.of(note));
        when(sources.findByUserIdAndKindAndRefId(userId, "note", noteId)).thenReturn(List.of(source));

        service.deleteNote(userId, noteId);

        assertThat(doc.getStatus()).isEqualTo("retired");
        verify(sources).delete(source);
        verify(notes).delete(note);
        // A typed note embeds text, so its copy names no object and the reclaim is asked about
        // nothing rather than about a null that would read as a key.
        verify(reclaimer).reclaim(List.of());
    }

    @Test
    void aNoteCopyThatWasUploadedIsReclaimedByDeletingTheNote() {
        KnowledgeSource source = source();
        source.setKind("note");
        source.setRefId(noteId);
        Document doc = document();
        when(documents.findBySourceId(any())).thenReturn(List.of(doc));
        UserNote note = mock(UserNote.class);
        when(note.getId()).thenReturn(noteId);
        when(notes.findByIdAndUserId(noteId, userId)).thenReturn(Optional.of(note));
        when(sources.findByUserIdAndKindAndRefId(userId, "note", noteId)).thenReturn(List.of(source));

        service.deleteNote(userId, noteId);

        // The note path asks the same question the source path asks, because the promise is about
        // the key: this delete takes the last row that named it.
        verify(reclaimer).reclaim(List.of(FILE_KEY));
    }

    @Test
    void anUnknownReferenceRetiresNothingAndDeletesNothing() {
        when(sources.findByUserIdAndKindAndRefId(userId, "resume", resumeId))
                .thenReturn(List.of());

        service.retireRef(userId, "resume", resumeId);

        verify(sources, never()).delete(any());
        verify(documents, never()).saveAll(any());
    }
}
