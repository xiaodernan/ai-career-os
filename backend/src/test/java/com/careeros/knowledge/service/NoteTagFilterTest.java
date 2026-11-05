package com.careeros.knowledge.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.knowledge.entity.UserNote;
import com.careeros.knowledge.repository.DocumentRepository;
import com.careeros.knowledge.repository.KnowledgeSourceRepository;
import com.careeros.knowledge.repository.UserNoteRepository;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;

/**
 * 64.2: the notes list can be narrowed to one tag.
 *
 * <p>The report's four keep actions write tags so the knowledge page can tell a
 * missing concept from a study item; without a filter that promise is only a
 * badge nobody can query on. The service is the seam that decides which read the
 * endpoint spends, so that decision is what this test pins: a tag asks the
 * tagged query, a blank one asks the list the page has always shown.
 */
class NoteTagFilterTest {

    private final UUID userId = UUID.randomUUID();

    private UserNoteRepository notes;
    private KnowledgeService service;

    @BeforeEach
    void setUp() {
        notes = mock(UserNoteRepository.class);
        service = new KnowledgeService(mock(KnowledgeSourceRepository.class),
                mock(DocumentRepository.class), notes, mock(FileIngestService.class),
                mock(StoredObjectReclaimer.class));
    }

    @Test
    void aTagNarrowsTheListToNotesThatCarryIt() {
        when(notes.findByTag(eq(userId), eq("gap"), any()))
                .thenReturn(new PageImpl<>(List.of(note("Why a B-tree keeps its leaves linked")),
                        PageRequest.of(0, 20), 1));

        var page = service.listNotes(userId, 0, 20, " gap ");

        assertThat(page.items()).hasSize(1);
        assertThat(page.total()).isEqualTo(1);
        verify(notes).findByTag(eq(userId), eq("gap"), any());
        verify(notes, never()).findByUserIdOrderByUpdatedAtDescIdAsc(any(), any());
    }

    @Test
    void noTagOrABlankOneAsksTheWholeList() {
        when(notes.findByUserIdOrderByUpdatedAtDescIdAsc(eq(userId), any()))
                .thenReturn(new PageImpl<>(List.of(note("a"), note("b")),
                        PageRequest.of(0, 20), 2));

        assertThat(service.listNotes(userId, 0, 20, null).total()).isEqualTo(2);
        assertThat(service.listNotes(userId, 0, 20, "   ").total()).isEqualTo(2);

        verify(notes, never()).findByTag(any(), any(), any());
    }

    private static UserNote note(String title) {
        UserNote note = new UserNote();
        note.setTitle(title);
        note.setContent(title);
        note.setTags(List.of("gap"));
        return note;
    }
}
