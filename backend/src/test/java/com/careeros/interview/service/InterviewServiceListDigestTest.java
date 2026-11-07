package com.careeros.interview.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.ai.AiServiceClient;
import com.careeros.common.PageDTO;
import com.careeros.interview.dto.InterviewDtos.SessionItem;
import com.careeros.interview.entity.InterviewSession;
import com.careeros.interview.repository.InterviewDigestRepository;
import com.careeros.interview.repository.InterviewDigestRepository.Digest;
import com.careeros.interview.repository.InterviewEvaluationRepository;
import com.careeros.interview.repository.InterviewSessionRepository;
import com.careeros.interview.repository.InterviewTurnRepository;
import com.careeros.job.repository.CompanyRepository;
import com.careeros.job.repository.JobRepository;
import com.careeros.support.TestTransactions;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;

/**
 * The list row has to say how far a session got and how it scored. Both live in child tables, so
 * the read is one batched lookup per page — and never an `IN ()` against an empty page.
 */
class InterviewServiceListDigestTest {

    private final UUID userId = UUID.randomUUID();
    private final UUID first = UUID.randomUUID();
    private final UUID second = UUID.randomUUID();

    private InterviewSessionRepository sessions;
    private InterviewDigestRepository digests;
    private com.careeros.application.service.ApplicationService applications;
    private InterviewService service;

    @BeforeEach
    void setUp() {
        sessions = mock(InterviewSessionRepository.class);
        digests = mock(InterviewDigestRepository.class);
        applications = mock(com.careeros.application.service.ApplicationService.class);
        when(applications.stagesOf(any(), any())).thenReturn(Map.of());
        service = new InterviewService(sessions, mock(InterviewTurnRepository.class),
                mock(InterviewEvaluationRepository.class), mock(JobRepository.class),
                mock(CompanyRepository.class), applications, digests,
                mock(AiServiceClient.class),
                TestTransactions.executing());
    }

    /** Ids come from the database (@UuidGenerator), so the entity is mocked to carry one. */
    private InterviewSession session(UUID id, String position) {
        InterviewSession s = mock(InterviewSession.class);
        when(s.getId()).thenReturn(id);
        when(s.getPositionTitle()).thenReturn(position);
        when(s.getMode()).thenReturn("technical");
        when(s.getStatus()).thenReturn("completed");
        return s;
    }

    private void givenPage(InterviewSession... rows) {
        when(sessions.findPage(any(), any(), any(), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(rows), PageRequest.of(0, 20), rows.length));
    }

    private List<SessionItem> listed() {
        PageDTO<SessionItem> page = service.list(userId, 0, 20, null, null);
        return page.items();
    }

    @Test
    void aCardIdNarrowsTheListToThatCardsRehearsals() {
        // 57.1: the drawer's "rehearsals" link lands on a list of this card's
        // sessions, so the filter has to be a second scope on the query -- not
        // something the browser re-filters after the fact, which would page
        // over the whole history and show a page of nothing.
        UUID card = UUID.randomUUID();
        InterviewSession row = session(first, "A");
        when(sessions.findPage(any(), any(), any(), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(row), PageRequest.of(0, 20), 1));
        when(digests.forSessions(any())).thenReturn(Map.of());

        List<SessionItem> items = service.list(userId, 0, 20, card, null).items();

        assertThat(items).hasSize(1);
        // One read for both questions now (70.4): the card id and the word ride the same query, and
        // an absent box arrives as the empty needle that narrows nothing rather than as a null that
        // would have to be spelled twice in the WHERE.
        verify(sessions).findPage(eq(userId), eq(card), eq(""), any(Pageable.class));
    }

    @Test
    void theWordArrivesTrimmedAndLowerCasedOnceForTheRequest() {
        givenPage(session(first, "A"));
        when(digests.forSessions(any())).thenReturn(Map.of());

        service.list(userId, 0, 20, null, "  AcMe  ");

        // The columns are lower-cased per row, so the needle has to be lower-cased here: a word
        // typed with Shift is the same question, and the padding around it is not part of it.
        verify(sessions).findPage(eq(userId), eq(null), eq("acme"), any(Pageable.class));
    }

    @Test
    void aBoxOfSpacesIsTheBoxNobodyTypedIn() {
        givenPage(session(first, "A"));
        when(digests.forSessions(any())).thenReturn(Map.of());

        service.list(userId, 0, 20, null, "   ");

        // A blank needle that filtered would open the board on nothing -- the reader asked to
        // browse, and spaces are the same empty question as no question at all.
        verify(sessions).findPage(eq(userId), eq(null), eq(""), any(Pageable.class));
    }

    @Test
    void theWordAndTheCardIdNarrowTheSameRead() {
        givenPage(session(first, "A"));
        when(digests.forSessions(any())).thenReturn(Map.of());
        UUID card = UUID.randomUUID();

        service.list(userId, 0, 20, card, "Acme");

        // Two scopes, one query: the card's rehearsals that spell the word, not the word over the
        // whole history and then a filter the browser applies to a page that already lost them.
        verify(sessions).findPage(eq(userId), eq(card), eq("acme"), any(Pageable.class));
    }

    @Test
    void theRowCarriesTheCardsStageReadOnceForThePage() {
        // 57.4: the list says whether the practice belongs to an application
        // still in play. The stage is one grouped read for the page, and a
        // rehearsal whose card is not in the answer carries none -- the row
        // must not invent a column for it.
        UUID card = UUID.randomUUID();
        InterviewSession withCard = session(first, "A");
        when(withCard.getApplicationId()).thenReturn(card);
        InterviewSession free = session(second, "B");
        givenPage(withCard, free);
        when(digests.forSessions(any())).thenReturn(Map.of());
        when(applications.stagesOf(any(), any())).thenReturn(Map.of(card, "interview"));

        List<SessionItem> items = listed();

        assertThat(items.get(0).applicationStatus()).isEqualTo("interview");
        assertThat(items.get(1).applicationStatus()).isNull();
        verify(applications).stagesOf(userId, List.of(card));
    }

    @Test
    void theRowCarriesTheQuestionCountAndScore() {
        givenPage(session(first, "Staff Backend Engineer"), session(second, "RAG Engineer"));
        when(digests.forSessions(any())).thenReturn(Map.of(
                first, new Digest(6, 0.75f),
                second, new Digest(2, null)));

        List<SessionItem> items = listed();

        assertThat(items.get(0).questionCount()).isEqualTo(6);
        assertThat(items.get(0).overall()).isEqualTo(0.75f);
        // a session nobody finalised has no score: an unattempted interview is not a zero
        assertThat(items.get(1).questionCount()).isEqualTo(2);
        assertThat(items.get(1).overall()).isNull();
    }

    @Test
    void theAggregatesAreFetchedOnceForTheWholePage() {
        givenPage(session(first, "A"), session(second, "B"));
        when(digests.forSessions(any())).thenReturn(Map.of());

        listed();

        ArgumentCaptor<Collection<UUID>> cap = ArgumentCaptor.forClass(Collection.class);
        verify(digests).forSessions(cap.capture());
        assertThat(cap.getValue()).containsExactlyInAnyOrder(first, second);
    }

    @Test
    void anEmptyPageReturnsNoRowsAndNeedsNoDigests() {
        givenPage();
        when(digests.forSessions(any())).thenReturn(Map.of());

        assertThat(listed()).isEmpty();

        // the empty-page guard lives in the repository (it protects every caller); the service
        // only has to survive being handed nothing
        verify(digests).forSessions(any());
    }

    @Test
    void singleRowReadsDoNotInventAggregates() {
        SessionItem item = InterviewService.toItem(session(first, "Staff Backend Engineer"));

        // detail/create/answer responses load no aggregates; claiming 0 questions there would be
        // as wrong as claiming the real number
        assertThat(item.questionCount()).isNull();
        assertThat(item.overall()).isNull();
        assertThat(item.positionTitle()).isEqualTo("Staff Backend Engineer");
    }
}
