package com.careeros.conversation.repository;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import com.careeros.conversation.repository.ConversationDigestRepository.Digest;
import jakarta.persistence.EntityManager;
import jakarta.persistence.Query;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

/**
 * The two grouped reads behind the copilot sidebar. A page of chats must cost two queries, not
 * two per row, and `WHERE conversation_id IN ()` is a syntax error — so the empty-page guard and
 * the statement shape both need checking rather than assuming.
 */
class ConversationDigestRepositoryTest {

    private final UUID a = UUID.randomUUID();
    private final UUID b = UUID.randomUUID();

    private EntityManager em;
    private Query query;
    private ConversationDigestRepository repo;

    @BeforeEach
    void setUp() {
        em = mock(EntityManager.class);
        query = mock(Query.class);
        repo = new ConversationDigestRepository(em);
        when(em.createNativeQuery(anyString())).thenReturn(query);
        when(query.setParameter(anyString(), any())).thenReturn(query);
    }

    private void answerWith(List<Object[]> rows) {
        when(query.getResultList()).thenReturn(rows);
    }

    /**
     * Rows for a stubbed result set. `List.of(row)` is not usable here: with a single array
     * argument Java spreads it, so a row whose preview column is null throws instead of
     * standing for that column being null.
     */
    private static List<Object[]> table(Object[]... rows) {
        return Arrays.asList(rows);
    }

    /** Counts from the first statement, previews from the second. */
    private void answers(List<Object[]> counts, List<Object[]> previews) {
        when(query.getResultList()).thenReturn(counts, previews);
    }

    /** The two statements the repository runs, in order. */
    private List<String> capturedSql() {
        ArgumentCaptor<String> sql = ArgumentCaptor.forClass(String.class);
        verify(em, times(2)).createNativeQuery(sql.capture());
        return sql.getAllValues();
    }

    @Test
    void anEmptyIdCollectionNeverReachesTheDatabase() {
        assertThat(repo.forConversations(List.of())).isEmpty();

        verifyNoInteractions(em);
    }

    @Test
    void aNullCollectionIsTreatedTheSameWay() {
        assertThat(repo.forConversations(null)).isEmpty();

        verifyNoInteractions(em);
    }

    @Test
    void aWholePageCostsTwoQueriesNotTwoPerConversation() {
        answerWith(List.of());

        repo.forConversations(List.of(a, b, UUID.randomUUID(), UUID.randomUUID()));

        // the N+1 shape this repository exists to remove: 2 statements, whatever the page size
        verify(em, times(2)).createNativeQuery(anyString());
    }

    @Test
    void theNewestMessagePerConversationComesFromAWindowNotAGroupBy() {
        answerWith(List.of());

        repo.forConversations(List.of(a));

        String last = capturedSql().get(1);
        assertThat(last).contains("row_number() OVER (PARTITION BY m.conversation_id");
        assertThat(last).contains("ORDER BY m.created_at DESC, m.id DESC");
        assertThat(last).contains("WHERE d.rn = 1");
        // a chat answer can be kilobytes of markdown and the sidebar shows one line
        assertThat(last).contains("left(m.content, 200)");
    }

    @Test
    void theIdCollectionIsBoundNotInterpolated() {
        answerWith(List.of());

        repo.forConversations(List.of(a, b));

        verify(query, times(2)).setParameter(eq("ids"), any());
        for (String statement : capturedSql()) {
            assertThat(statement).contains("IN (:ids)");
            assertThat(statement).doesNotContain(a.toString());
        }
    }

    @Test
    void countsAndPreviewsMergeIntoOneDigestPerConversation() {
        // both statements answer for the same ids here; the merge must keep each side's own fact
        answers(table(new Object[] {a, 4L}, new Object[] {b, 2L}),
                table(new Object[] {a, "the answer"}, new Object[] {b, "still open"}));

        Map<UUID, Digest> out = repo.forConversations(List.of(a, b));

        assertThat(out).hasSize(2);
        assertThat(out.get(a).messageCount()).isEqualTo(4);
        assertThat(out.get(a).lastMessage()).isEqualTo("the answer");
        assertThat(out.get(b).messageCount()).isEqualTo(2);
        assertThat(out.get(b).lastMessage()).isEqualTo("still open");
    }

    @Test
    void aChatWithNoMessagesHasZeroOfThemAndNothingToPreview() {
        answers(table(), table());

        Map<UUID, Digest> out = repo.forConversations(List.of(a));

        // GROUP BY omits the row entirely: absent counts here mean zero, not "unknown" —
        // but an empty-string preview would render as a blank line that looks like data.
        assertThat(out.get(a).messageCount()).isZero();
        assertThat(out.get(a).lastMessage()).isNull();
    }

    @Test
    void aBlankStoredContentIsReadAsNoPreviewRatherThanAnEmptyString() {
        answers(table(new Object[] {a, 1L}), table(new Object[] {a, null}));

        Map<UUID, Digest> out = repo.forConversations(List.of(a));

        assertThat(out.get(a).lastMessage()).isNull();
        assertThat(out.get(a).messageCount()).isEqualTo(1);
    }
}
