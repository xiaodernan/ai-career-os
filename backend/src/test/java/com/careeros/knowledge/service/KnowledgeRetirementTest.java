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
 */
class KnowledgeRetirementTest {

    private final UUID userId = UUID.randomUUID();
    private final UUID sourceId = UUID.randomUUID();
    private final UUID documentId = UUID.randomUUID();
    private final UUID resumeId = UUID.randomUUID();
    private final UUID noteId = UUID.randomUUID();

    private KnowledgeSourceRepository sources;
    private DocumentRepository documents;
    private UserNoteRepository notes;
    private KnowledgeService service;

    @BeforeEach
    void setUp() {
        sources = mock(KnowledgeSourceRepository.class);
        documents = mock(DocumentRepository.class);
        notes = mock(UserNoteRepository.class);
        service = new KnowledgeService(sources, documents, notes, mock(FileIngestService.class));
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
        Document doc = new Document();
        doc.setUserId(userId);
        doc.setSourceId(sourceId);
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
    }

    @Test
    void deletingTheDomainRowRetiresTheIngestedCopyToo() {
        KnowledgeSource source = source();
        Document doc = document();
        when(documents.findBySourceId(any())).thenReturn(List.of());
        when(sources.findByUserIdAndKindAndRefId(userId, "resume", resumeId))
                .thenReturn(List.of(source));

        service.retireRef(userId, "resume", resumeId);

        // retirement has to work through knowledge_sources.document_id alone — that is the
        // link the ingest callback sets, and the resume path relies on it.
        assertThat(doc.getStatus()).isEqualTo("retired");
        verify(sources).delete(source);
    }

    @Test
    void theSameDocumentReachedByBothLinksIsRetiredOnce() {
        KnowledgeSource source = source();
        Document doc = document();
        when(documents.findBySourceId(any())).thenReturn(List.of(doc));
        when(sources.findByUserIdAndKindAndRefId(userId, "resume", resumeId))
                .thenReturn(List.of(source));

        service.retireRef(userId, "resume", resumeId);

        assertThat(doc.getStatus()).isEqualTo("retired");
        verify(sources).delete(source);
    }

    @Test
    void deletingANoteRetiresItsEmbeddedCopy() {
        KnowledgeSource source = source();
        Document doc = document();
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
