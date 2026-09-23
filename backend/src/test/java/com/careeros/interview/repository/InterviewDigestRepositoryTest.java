package com.careeros.interview.repository;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import com.careeros.interview.repository.InterviewDigestRepository.Digest;
import jakarta.persistence.EntityManager;
import jakarta.persistence.Query;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

/**
 * The two grouped reads behind the interview list. `WHERE id IN ()` is a syntax error and
 * `('five')::real` is a runtime error, so both statements need their guards checked, not assumed.
 */
class InterviewDigestRepositoryTest {

    private final UUID a = UUID.randomUUID();
    private final UUID b = UUID.randomUUID();

    private EntityManager em;
    private Query query;
    private InterviewDigestRepository repo;

    @BeforeEach
    void setUp() {
        em = mock(EntityManager.class);
        query = mock(Query.class);
        repo = new InterviewDigestRepository(em);
        when(em.createNativeQuery(anyString())).thenReturn(query);
        when(query.setParameter(anyString(), org.mockito.ArgumentMatchers.any())).thenReturn(query);
    }

    private void answerWith(List<Object[]> rows) {
        when(query.getResultList()).thenReturn(rows);
    }

    @Test
    void anEmptyIdCollectionNeverReachesTheDatabase() {
        assertThat(repo.forSessions(List.of())).isEmpty();

        verifyNoInteractions(em);
    }

    @Test
    void aNullCollectionIsTreatedTheSameWay() {
        assertThat(repo.forSessions(null)).isEmpty();

        verifyNoInteractions(em);
    }

    @Test
    void onlyInterviewerTurnsCountAsQuestions() {
        answerWith(List.of());

        repo.forSessions(List.of(a));

        ArgumentCaptor<String> sql = ArgumentCaptor.forClass(String.class);
        verify(em, org.mockito.Mockito.times(2)).createNativeQuery(sql.capture());
        String counts = sql.getAllValues().get(0);
        assertThat(counts).contains("t.role = 'interviewer'");
        assertThat(counts).contains("GROUP BY t.session_id");
        assertThat(counts).doesNotContain("candidate");
    }

    @Test
    void aNonNumericScoreIsReadAsNoScoreInsteadOfFailingThePage() {
        answerWith(List.of());

        repo.forSessions(List.of(a));

        ArgumentCaptor<String> sql = ArgumentCaptor.forClass(String.class);
        verify(em, org.mockito.Mockito.times(2)).createNativeQuery(sql.capture());
        String scores = sql.getAllValues().get(1);
        assertThat(scores).contains("jsonb_typeof(e.summary -> 'overall') = 'number'");
        assertThat(scores).contains("::real");
    }

    @Test
    void theIdCollectionIsBoundNotInterpolated() {
        answerWith(List.of());

        repo.forSessions(List.of(a, b));

        verify(query, org.mockito.Mockito.atLeast(2)).setParameter(org.mockito.ArgumentMatchers.eq("ids"),
                org.mockito.ArgumentMatchers.any());
        ArgumentCaptor<String> sql = ArgumentCaptor.forClass(String.class);
        verify(em, org.mockito.Mockito.times(2)).createNativeQuery(sql.capture());
        for (String statement : sql.getAllValues()) {
            assertThat(statement).contains("IN (:ids)");
            assertThat(statement).doesNotContain(a.toString());
        }
    }

    @Test
    void countedRowsAndScoresMergeIntoOneDigestPerSession() {
        answerWith(List.of(new Object[] {a, 7L}, new Object[] {b, 10.0f}));

        Map<UUID, Digest> out = repo.forSessions(List.of(a, b));

        // both queries answer for the same ids here; the merge keeps count from the first and
        // score from the second, so what matters is that neither is lost
        assertThat(out).hasSize(2);
        assertThat(out.get(a).questions()).isEqualTo(7);
        assertThat(out.get(a).overall()).isNotNull();
    }

    @Test
    void aSessionWithNoTurnsReportsZeroQuestionsAndNoScore() {
        answerWith(List.of());

        Map<UUID, Digest> out = repo.forSessions(List.of(a));

        assertThat(out.get(a).questions()).isZero();
        assertThat(out.get(a).overall()).isNull();
    }
}
