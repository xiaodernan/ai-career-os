package com.careeros.knowledge.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.knowledge.dto.KnowledgeDtos.NoteRequest;
import com.careeros.knowledge.entity.UserNote;
import com.careeros.knowledge.repository.DocumentRepository;
import com.careeros.knowledge.repository.KnowledgeSourceRepository;
import com.careeros.knowledge.repository.UserNoteRepository;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

/**
 * A note the reader wrote has to be quotable.
 *
 * <p>The panel promises it three times over: the content field says "the agents
 * can quote this back with a citation", the section says "short reference notes
 * the agents can quote back at you", and deleting a note says "the note row is
 * removed and its chunks stop being cited".
 *
 * <p>Two of those three were true and the first was not. The note was a row
 * in {@code user_notes} and nothing more: the retrieval layer admits a chunk
 * only while its document row reads 'ready', and a note that was never
 * ingested has no document and no chunk, so no agent could ever quote it. The
 * delete path was written for a note that <em>had</em> an embedded copy --
 * it retires the note's source by kind and reference -- which is a retire of
 * nothing.
 *
 * <p>So the note is ingested, with the kind and the reference that make it
 * quotable and retirable, and an edit retires the old copy before the new one
 * lands: the reader deleted a sentence and the assistant kept quoting it.
 */
class NoteCitationTest {

    private final UUID userId = UUID.randomUUID();
    private final UUID noteId = UUID.randomUUID();

    private KnowledgeSourceRepository sources;
    private DocumentRepository documents;
    private UserNoteRepository notes;
    private FileIngestService fileIngest;
    private KnowledgeService service;

    @BeforeEach
    void setUp() {
        sources = mock(KnowledgeSourceRepository.class);
        documents = mock(DocumentRepository.class);
        notes = mock(UserNoteRepository.class);
        fileIngest = mock(FileIngestService.class);
        service = new KnowledgeService(sources, documents, notes, fileIngest);
    }

    @Test
    void writingANoteIngestesItsTextSoTheAgentsCanQuoteIt() {
        when(notes.saveAndFlush(any())).thenAnswer(call -> call.getArgument(0));

        service.createNote(userId, new NoteRequest("Salary research", "Hangzhou pays 40-60w.", List.of()));

        // The kind is "note" and the reference is the note's own id: that is
        // what the delete path retires, and what makes the copy retirable at
        // all.
        verify(fileIngest).ingestText(eq(userId), eq("Salary research"),
                eq("Hangzhou pays 40-60w."), eq("note"), any());
    }

    @Test
    void editingANoteRetiresTheOldCopyAndIngestsTheNewOne() {
        UserNote note = mock(UserNote.class);
        when(note.getId()).thenReturn(noteId);
        when(note.getTitle()).thenReturn("Salary research");
        when(note.getContent()).thenReturn("Hangzhou pays 45-65w.");
        when(notes.findByIdAndUserId(noteId, userId)).thenReturn(Optional.of(note));
        when(sources.findByUserIdAndKindAndRefId(userId, "note", noteId)).thenReturn(List.of());

        service.updateNote(userId, noteId, new NoteRequest("Salary research", "Hangzhou pays 45-65w.", List.of()));

        // The old copy goes first: the reader deleted a sentence and the
        // assistant must stop quoting it.
        verify(sources).findByUserIdAndKindAndRefId(userId, "note", noteId);
        verify(fileIngest).ingestText(eq(userId), eq("Salary research"),
                eq("Hangzhou pays 45-65w."), eq("note"), eq(noteId));
    }

    @Test
    void aFailedIngestDoesNotCostTheReaderTheirNote() {
        when(notes.saveAndFlush(any())).thenAnswer(call -> call.getArgument(0));
        org.mockito.Mockito.doThrow(new IllegalStateException("the engine is down"))
                .when(fileIngest).ingestText(any(), any(), any(), any(), any());

        // The note is the reader's; the copy the agents quote is derived. A
        // derived copy that failed to build is not a reason to refuse the note.
        var item = service.createNote(userId, new NoteRequest("A note", "Some words.", List.of()));

        assertThat(item).isNotNull();
        verify(notes).saveAndFlush(any());
    }

    @Test
    void aNoteWithNoWordsIsNotIngested() {
        when(notes.saveAndFlush(any())).thenAnswer(call -> call.getArgument(0));

        service.createNote(userId, new NoteRequest("A note", "   ", List.of()));

        // There is nothing to quote, and an empty document would be a source
        // with nothing in it.
        verify(fileIngest, never()).ingestText(any(), any(), any(), any(), any());
    }
}
