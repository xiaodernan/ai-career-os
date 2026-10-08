package com.careeros.interview.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
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
    private InterviewService service;

    @BeforeEach
    void setUp() {
        sessions = mock(InterviewSessionRepository.class);
        digests = mock(InterviewDigestRepository.class);
        service = new InterviewService(sessions, mock(InterviewTurnRepository.class),
                mock(InterviewEvaluationRepository.class), mock(JobRepository.class),
                mock(CompanyRepository.class), digests, mock(AiServiceClient.class));
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
        when(sessions.findByUserIdOrderByStartedAtDescIdAsc(any(), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(rows), PageRequest.of(0, 20), rows.length));
    }

    private List<SessionItem> listed() {
        PageDTO<SessionItem> page = service.list(userId, 0, 20);
        return page.items();
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
