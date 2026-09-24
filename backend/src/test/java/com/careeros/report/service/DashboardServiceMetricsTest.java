package com.careeros.report.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.activity.repository.AgentRunRepository;
import com.careeros.application.repository.ApplicationEventRepository;
import com.careeros.application.repository.ApplicationRepository;
import com.careeros.interview.repository.InterviewSessionRepository;
import com.careeros.job.repository.JobMatchRepository;
import com.careeros.job.repository.JobRepository;
import com.careeros.report.dto.DashboardDtos.DashboardResponse;
import com.careeros.report.repository.DashboardRepository;
import com.careeros.resume.service.ResumeService;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/**
 * The two stat-strip aggregates in {@link DashboardService#build}: the response must carry them
 * straight from {@link DashboardRepository} with the service's own staleness window, because the
 * landing page's fourth card has no other source. Null-average propagation is pinned here too — a
 * null turned into 0f at this seam would draw a 0% match ring for a user who has never scored a
 * job, which is the exact failure the read is written to avoid. Only the dashboard repo is
 * stubbed; every other collaborator returns Mockito's empty defaults.
 */
class DashboardServiceMetricsTest {

    private final UUID userId = UUID.randomUUID();

    private DashboardRepository dashboard;
    private DashboardService service;

    @BeforeEach
    void setUp() {
        dashboard = mock(DashboardRepository.class);
        service = new DashboardService(mock(ApplicationRepository.class),
                mock(ApplicationEventRepository.class),
                mock(InterviewSessionRepository.class),
                mock(ResumeService.class),
                mock(JobRepository.class),
                mock(JobMatchRepository.class),
                mock(AgentRunRepository.class),
                dashboard);
    }

    @Test
    void carriesTheAverageMatchFromTheRepository() {
        when(dashboard.averageMatch(userId)).thenReturn(0.72f);
        assertThat(service.build(userId).avgMatch()).isEqualTo(0.72f);
    }

    @Test
    void unscoredAccountReportsNoAverageRatherThanZero() {
        // Stubbed rather than left to Mockito's default, which answers a Float with 0f. What this
        // pins is the service: it must pass the null through instead of coercing a stale-looking
        // zero into the payload.
        when(dashboard.averageMatch(userId)).thenReturn(null);
        assertThat(service.build(userId).avgMatch()).isNull();
    }

    @Test
    void needsAttentionUsesTheServicesStalenessWindow() {
        when(dashboard.needsAttention(userId, 14)).thenReturn(5L);
        DashboardResponse response = service.build(userId);
        assertThat(response.needsAttention()).isEqualTo(5L);
        verify(dashboard).needsAttention(userId, 14);
    }
}
