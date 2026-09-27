package com.careeros.knowledge.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.common.PageDTO;
import com.careeros.knowledge.dto.KnowledgeDtos.SourceItem;
import com.careeros.knowledge.entity.KnowledgeSource;
import com.careeros.knowledge.repository.DocumentRepository;
import com.careeros.knowledge.repository.KnowledgeSourceRepository;
import com.careeros.knowledge.repository.UserNoteRepository;
import java.lang.reflect.Method;
import java.util.Arrays;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.Pageable;
import org.springframework.data.repository.query.parser.Part;
import org.springframework.data.repository.query.parser.PartTree;

/**
 * `GET /knowledge/sources?documentId=` is what turns a citation's link into a link.
 *
 * The id a citation carries is the document its chunk came from, while a row of this list is a
 * `knowledge_sources` record that points at that document — two tables, and matching the link against
 * the row's own id would answer every citation with an empty page and look like a deleted source. So
 * both halves are checked: which finder the service asks for, and that the finder's derived name really
 * filters on the document column rather than on some other UUID the entity also happens to own.
 */
class KnowledgeSourceListingTest {

    private final UUID userId = UUID.randomUUID();
    private final UUID documentId = UUID.randomUUID();

    private KnowledgeSourceRepository sources;
    private KnowledgeService service;

    @BeforeEach
    void setUp() {
        sources = mock(KnowledgeSourceRepository.class);
        service = new KnowledgeService(sources, mock(DocumentRepository.class),
                mock(UserNoteRepository.class), mock(FileIngestService.class));
    }

    private Page<KnowledgeSource> one() {
        KnowledgeSource source = new KnowledgeSource();
        source.setUserId(userId);
        source.setDocumentId(documentId);
        source.setKind("resume");
        source.setTitle("resume.pdf");
        source.setStatus("ready");
        return new PageImpl<>(List.of(source));
    }

    @Test
    void aNamedDocumentNarrowsTheListToItsSource() {
        when(sources.findByUserIdAndDocumentIdOrderByCreatedAtDesc(any(), any(), any())).thenReturn(one());

        PageDTO<SourceItem> page = service.listSources(userId, 0, 20, documentId);

        verify(sources).findByUserIdAndDocumentIdOrderByCreatedAtDesc(
                eq(userId), eq(documentId), any(Pageable.class));
        verify(sources, never()).findByUserIdOrderByCreatedAtDesc(any(), any());
        assertThat(page.items()).extracting(SourceItem::documentId).containsExactly(documentId);
    }

    @Test
    void noDocumentNamedIsTheWholeBoard() {
        when(sources.findByUserIdOrderByCreatedAtDesc(any(), any())).thenReturn(one());

        service.listSources(userId, 0, 20, null);

        verify(sources).findByUserIdOrderByCreatedAtDesc(eq(userId), any(Pageable.class));
        verify(sources, never()).findByUserIdAndDocumentIdOrderByCreatedAtDesc(any(), any(), any());
    }

    /**
     * The derived query is a name, and a name is free to be wrong: Spring Data resolves it at context
     * startup, which an offline unit test never reaches, and the entity carries several UUID columns.
     * So the property the finder filters on is read out of the shipped repository declaration — renaming
     * the method breaks this test rather than quietly changing which column the link matches.
     */
    @Test
    void theFinderFiltersOnTheDocumentColumn() {
        String declared = Arrays.stream(KnowledgeSourceRepository.class.getDeclaredMethods())
                .map(Method::getName)
                .filter(name -> name.startsWith("findByUserIdAnd"))
                .filter(name -> name.contains("OrderByCreatedAtDesc"))
                .findFirst()
                .orElseThrow(() -> new AssertionError("no per-document source finder is declared"));

        List<String> properties = new PartTree(declared, KnowledgeSource.class).getParts()
                .stream().map(Part::getProperty).map(Object::toString).toList();
        // Qualified with the entity, which is the point: the name Spring Data will resolve is read off
        // the shipped declaration, so a finder that filters some other column cannot pass by matching a
        // name this test typed out itself.
        assertThat(properties).containsExactly("KnowledgeSource.userId", "KnowledgeSource.documentId");
    }

    /**
     * Positive control: the reader above really does tell the document column from the other UUID the
     * entity owns. Without this line a check that accepted any single property would pass on the
     * sibling column, which is the exact mistake the test exists to catch.
     */
    @Test
    void theSameReaderNamesTheSiblingColumnWhenThatIsWhatIsDeclared() {
        List<String> properties = new PartTree(
                "findByUserIdAndRefIdOrderByCreatedAtDesc", KnowledgeSource.class)
                .getParts().stream().map(Part::getProperty).map(Object::toString).toList();
        assertThat(properties).containsExactly("KnowledgeSource.userId", "KnowledgeSource.refId");
    }
}
