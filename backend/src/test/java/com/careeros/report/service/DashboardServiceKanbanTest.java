package com.careeros.report.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.careeros.activity.repository.AgentRunRepository;
import com.careeros.application.repository.ApplicationEventRepository;
import com.careeros.application.repository.ApplicationRepository;
import com.careeros.application.service.ApplicationService;
import com.careeros.interview.repository.InterviewSessionRepository;
import com.careeros.job.repository.JobMatchRepository;
import com.careeros.job.repository.JobRepository;
import com.careeros.report.dto.DashboardDtos.DashboardResponse;
import com.careeros.report.dto.DashboardDtos.Kanban;
import com.careeros.report.repository.DashboardRepository;
import com.careeros.resume.service.ResumeService;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/**
 * Kanban aggregation in {@link DashboardService#build}: the response must always carry a column
 * for every {@link ApplicationService#STATUSES} value — even the ones with zero applications —
 * because the UI renders columns straight off this map, so a dropped zero-seed silently deletes
 * empty columns. Also locks that {@code total} is the sum across all reported rows and that
 * {@code offers} is lifted from the "offer" column. Only statusCounts is stubbed: every other
 * collaborator returns Mockito's empty defaults (Optional.empty / empty list / 0), which keeps the
 * resume/skill-gap/recent lists null-or-empty without touching the aggregation under test.
 */
class DashboardServiceKanbanTest {

    private final UUID userId = UUID.randomUUID();

    private ApplicationRepository applications;
    private DashboardService service;

    @BeforeEach
    void setUp() {
        applications = mock(ApplicationRepository.class);
        service = new DashboardService(applications,
                mock(ApplicationEventRepository.class),
                mock(InterviewSessionRepository.class),
                mock(ResumeService.class),
                mock(JobRepository.class),
                mock(JobMatchRepository.class),
                mock(AgentRunRepository.class),
                mock(DashboardRepository.class));
    }

    private Kanban kanbanFor(List<Object[]> rows) {
        when(applications.statusCounts(userId)).thenReturn(rows);
        return service.build(userId).kanban();
    }

    @Test
    void emptyPipelineStillRendersEveryStatusColumnAtZero() {
        Kanban kanban = kanbanFor(List.of());

        Map<String, Long> counts = kanban.statusCounts();
        assertThat(counts).containsOnlyKeys(ApplicationService.STATUSES);
        assertThat(counts.values()).containsOnly(0L);
        assertThat(kanban.total()).isZero();
        assertThat(kanban.offers()).isZero();
    }

    @Test
    void reportedStatusesAreCountedAndUnreportedOnesStayZero() {
        Kanban kanban = kanbanFor(List.of(
                new Object[] {"saved", 2L},
                new Object[] {"interview", 1L},
                new Object[] {"offer", 4L},
                new Object[] {"rejected", 1L}));

        Map<String, Long> counts = kanban.statusCounts();
        // The four reported columns carry their counts...
        assertThat(counts)
                .containsEntry("saved", 2L)
                .containsEntry("interview", 1L)
                .containsEntry("offer", 4L)
                .containsEntry("rejected", 1L);
        // ...and the three statuses with no applications are seeded to zero, never absent.
        assertThat(counts)
                .containsEntry("applied", 0L)
                .containsEntry("oa", 0L)
                .containsEntry("final_round", 0L);
        assertThat(counts).hasSize(7).containsOnlyKeys(ApplicationService.STATUSES);

        assertThat(kanban.total()).isEqualTo(8L);
        assertThat(kanban.offers()).isEqualTo(4L);
    }

    @Test
    void totalSumsEveryColumnAndOffersTracksTheOfferBucket() {
        // Every status present, including an offer bucket that must be mirrored into offers().
        Kanban kanban = kanbanFor(List.of(
                new Object[] {"saved", 1L},
                new Object[] {"applied", 2L},
                new Object[] {"oa", 3L},
                new Object[] {"interview", 4L},
                new Object[] {"final_round", 5L},
                new Object[] {"offer", 6L},
                new Object[] {"rejected", 7L}));

        assertThat(kanban.total()).isEqualTo(28L);
        assertThat(kanban.offers()).isEqualTo(6L);
    }
}
