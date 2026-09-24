package com.careeros.report.service;

import com.careeros.activity.entity.AgentRun;
import com.careeros.activity.repository.AgentRunRepository;
import com.careeros.application.entity.ApplicationEvent;
import com.careeros.application.repository.ApplicationEventRepository;
import com.careeros.application.repository.ApplicationRepository;
import com.careeros.application.service.ApplicationService;
import com.careeros.interview.repository.InterviewSessionRepository;
import com.careeros.job.entity.Job;
import com.careeros.job.entity.JobMatch;
import com.careeros.job.repository.JobMatchRepository;
import com.careeros.job.repository.JobRepository;
import com.careeros.report.dto.DashboardDtos.DashboardResponse;
import com.careeros.report.dto.DashboardDtos.Kanban;
import com.careeros.report.dto.DashboardDtos.RecentActivity;
import com.careeros.report.dto.DashboardDtos.RecentRun;
import com.careeros.report.dto.DashboardDtos.ResumeSummary;
import com.careeros.report.dto.DashboardDtos.SkillGapDigest;
import com.careeros.report.repository.DashboardRepository;
import com.careeros.resume.service.ResumeService;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * GET /api/v1/reports/dashboard — one aggregated, read-only snapshot. Every collection is fetched in
 * a single query (group-by counts, lateral match join) so the endpoint never fans out per row.
 */
@Service
public class DashboardService {

    private static final int RECOMMENDED_LIMIT = 5;
    private static final int RECENT_LIMIT = 5;
    /** An application nobody has logged a step on for this long is the user's to chase. */
    private static final int STALE_DAYS = 14;

    private final ApplicationRepository applications;
    private final ApplicationEventRepository appEvents;
    private final InterviewSessionRepository interviews;
    private final ResumeService resumes;
    private final JobRepository jobs;
    private final JobMatchRepository matches;
    private final AgentRunRepository runs;
    private final DashboardRepository dashboard;

    public DashboardService(ApplicationRepository applications, ApplicationEventRepository appEvents,
                            InterviewSessionRepository interviews, ResumeService resumes, JobRepository jobs,
                            JobMatchRepository matches, AgentRunRepository runs, DashboardRepository dashboard) {
        this.applications = applications;
        this.appEvents = appEvents;
        this.interviews = interviews;
        this.resumes = resumes;
        this.jobs = jobs;
        this.matches = matches;
        this.runs = runs;
        this.dashboard = dashboard;
    }

    @Transactional(readOnly = true)
    public DashboardResponse build(UUID userId) {
        return new DashboardResponse(
                kanban(userId),
                interviews.countByUserId(userId),
                dashboard.averageMatch(userId),
                dashboard.needsAttention(userId, STALE_DAYS),
                currentResume(userId),
                skillGaps(userId),
                dashboard.recommendedJobs(userId, RECOMMENDED_LIMIT),
                recentRuns(userId),
                recentActivity(userId));
    }

    private Kanban kanban(UUID userId) {
        Map<String, Long> counts = new LinkedHashMap<>();
        for (String status : ApplicationService.STATUSES) {
            counts.put(status, 0L);
        }
        long total = 0;
        for (Object[] row : applications.statusCounts(userId)) {
            String status = (String) row[0];
            long count = ((Number) row[1]).longValue();
            counts.put(status, count);
            total += count;
        }
        return new Kanban(counts, total, counts.getOrDefault("offer", 0L));
    }

    private ResumeSummary currentResume(UUID userId) {
        return resumes.currentResumeWithVersion(userId)
                .flatMap(resume -> resumes.currentVersion(resume)
                        .map(version -> new ResumeSummary(resume.getId(), version.getId(), resume.getTitle(),
                                resume.getStatus(), version.getScore())))
                .orElse(null);
    }

    private SkillGapDigest skillGaps(UUID userId) {
        JobMatch best = matches.findFirstByUserIdOrderByOverallDesc(userId).orElse(null);
        if (best == null) {
            return null;
        }
        String jobTitle = jobs.findById(best.getJobId()).map(Job::getTitle).orElse(null);
        return new SkillGapDigest(best.getJobId(), jobTitle, best.getOverall(),
                best.getMissingSkills(), best.getMatchedSkills());
    }

    private List<RecentRun> recentRuns(UUID userId) {
        return runs.findRecent(userId, null, PageRequest.of(0, RECENT_LIMIT)).stream()
                .map(DashboardService::toRun).toList();
    }

    private List<RecentActivity> recentActivity(UUID userId) {
        return appEvents.findByUserIdOrderByCreatedAtDesc(userId, PageRequest.of(0, RECENT_LIMIT)).stream()
                .map(DashboardService::toActivity).toList();
    }

    private static RecentRun toRun(AgentRun r) {
        return new RecentRun(r.getId(), r.getAgent(), r.getTrigger(), r.getStatus(), r.getModel(),
                r.getInputTokens(), r.getOutputTokens(), r.getCostUsd(), r.getStartedAt(), r.getFinishedAt());
    }

    private static RecentActivity toActivity(ApplicationEvent e) {
        return new RecentActivity(e.getId(), e.getApplicationId(), e.getKind(), e.getPayload(), e.getCreatedAt());
    }
}
