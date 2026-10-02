package com.careeros.application.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.application.entity.Application;
import com.careeros.application.repository.ApplicationEventRepository;
import com.careeros.application.repository.ApplicationRepository;
import com.careeros.job.repository.CompanyRepository;
import com.careeros.job.repository.JobRepository;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

/**
 * The link columns are written by the pipeline, not the user: `linkJobActivity` is what the match,
 * tailor and JD-analysis routes call so a tracker card can say which resume, JD analysis and match
 * stand behind it.
 *
 * <p>Plain Mockito — no DB, no Spring context. The two rules that matter are here rather than in an
 * integration test: a null argument must leave its column alone (tailoring must not clear the match
 * the same row already carries), and an unchanged value must not be written, because re-running a
 * match against the same resume is otherwise a write per click.
 */
class ApplicationServiceLinkTest {

    private final UUID userId = UUID.randomUUID();
    private final UUID jobId = UUID.randomUUID();

    private ApplicationRepository applications;
    private ApplicationEventRepository events;
    private ApplicationService service;

    @BeforeEach
    void setUp() {
        applications = mock(ApplicationRepository.class);
        events = mock(ApplicationEventRepository.class);
        service = new ApplicationService(applications, events,
                mock(JobRepository.class), mock(CompanyRepository.class));
    }

    private Application tracked(String status) {
        Application app = new Application();
        app.setUserId(userId);
        app.setJobId(jobId);
        app.setStatus(status);
        when(applications.findByUserIdAndJobId(userId, jobId)).thenReturn(List.of(app));
        return app;
    }

    @Test
    void fillsTheColumnsTheActionProduced() {
        Application app = tracked("applied");
        UUID rv = UUID.randomUUID();
        UUID jd = UUID.randomUUID();
        UUID match = UUID.randomUUID();

        assertThat(service.linkJobActivity(userId, jobId, rv, jd, match)).isEqualTo(1);

        assertThat(app.getResumeVersionId()).isEqualTo(rv);
        assertThat(app.getJdId()).isEqualTo(jd);
        assertThat(app.getMatchId()).isEqualTo(match);
        verify(applications).save(app);
    }

    @Test
    void aNullArgumentLeavesItsColumnAsItWas() {
        Application app = tracked("interview");
        UUID existingMatch = UUID.randomUUID();
        app.setMatchId(existingMatch);
        UUID rv = UUID.randomUUID();

        // Tailoring: a resume, no JD and no match. The match the row already had must survive, or
        // tailoring a job would erase the evidence the card is built on.
        assertThat(service.linkJobActivity(userId, jobId, rv, null, null)).isEqualTo(1);

        assertThat(app.getResumeVersionId()).isEqualTo(rv);
        assertThat(app.getMatchId()).isEqualTo(existingMatch);
        assertThat(app.getJdId()).isNull();
    }

    @Test
    void anUnchangedValueIsNotAWrite() {
        Application app = tracked("applied");
        UUID rv = UUID.randomUUID();
        app.setResumeVersionId(rv);
        app.setMatchId(UUID.randomUUID());

        assertThat(service.linkJobActivity(userId, jobId, rv, null, null)).isZero();

        verify(applications, never()).save(any(Application.class));
    }

    @Test
    void anActionWithNothingToLinkAndAJoblessAnalysisAreBothNoOps() {
        tracked("saved");

        assertThat(service.linkJobActivity(userId, jobId, null, null, null)).isZero();
        // A pasted JD with no job (the paste-only path) has no row to point at it.
        assertThat(service.linkJobActivity(userId, null, null, UUID.randomUUID(), null)).isZero();

        verify(applications, never()).save(any(Application.class));
        verify(applications, never()).findByUserIdAndJobId(any(), any());
    }

    @Test
    void everyRowTheUserTracksForThatJobIsLinkedAndNoOtherUsersAreRead() {
        Application first = new Application();
        first.setUserId(userId);
        first.setJobId(jobId);
        Application second = new Application();
        second.setUserId(userId);
        second.setJobId(jobId);
        UUID match = UUID.randomUUID();
        when(applications.findByUserIdAndJobId(userId, jobId)).thenReturn(List.of(first, second));

        assertThat(service.linkJobActivity(userId, jobId, null, null, match)).isEqualTo(2);

        ArgumentCaptor<Application> saved = ArgumentCaptor.forClass(Application.class);
        verify(applications, times(2)).save(saved.capture());
        assertThat(saved.getAllValues()).containsExactly(first, second);
        assertThat(saved.getAllValues()).allSatisfy(a -> assertThat(a.getMatchId()).isEqualTo(match));
        // The lookup is the user-scoped one: a link write must not be able to reach another account's
        // card for the same job.
        verify(applications).findByUserIdAndJobId(userId, jobId);
    }
}
