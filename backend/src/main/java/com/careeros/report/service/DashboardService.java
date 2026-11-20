package com.careeros.report.service;

import com.careeros.activity.entity.AgentRun;
import com.careeros.activity.repository.AgentRunRepository;
import com.careeros.ai.AiServiceClient;
import com.careeros.application.entity.ApplicationEvent;
import com.careeros.application.repository.ApplicationEventRepository;
import com.careeros.application.repository.ApplicationRepository;
import com.careeros.application.service.ApplicationService;
import com.careeros.algorithm.Recommendation;
import com.careeros.algorithm.TopK;
import com.careeros.common.Paging;
import com.careeros.interview.repository.InterviewSessionRepository;
import com.careeros.job.entity.Job;
import com.careeros.job.entity.JobMatch;
import com.careeros.job.repository.JobMatchRepository;
import com.careeros.job.repository.JobRepository;
import com.careeros.report.dto.DashboardDtos.DashboardResponse;
import com.careeros.report.dto.DashboardDtos.FollowUpItem;
import com.careeros.report.dto.DashboardDtos.Kanban;
import com.careeros.report.dto.DashboardDtos.RecentActivity;
import com.careeros.report.dto.DashboardDtos.RecentRun;
import com.careeros.report.dto.DashboardDtos.RecommendedJob;
import com.careeros.report.dto.DashboardDtos.ResumeSummary;
import com.careeros.report.dto.DashboardDtos.SkillGapDigest;
import com.careeros.report.repository.DashboardRepository;
import com.careeros.resume.service.ResumeService;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * GET /api/v1/reports/dashboard — one aggregated, read-only snapshot. Every collection is fetched in
 * a single query (group-by counts, lateral match join) so the endpoint never fans out per row.
 */
@Service
public class DashboardService {

    private static final int RECOMMENDED_LIMIT = 5;
    /** Rows behind the attention count: what one card can list before nobody reads it. */
    private static final int ATTENTION_LIMIT = 5;
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
    private final AiServiceClient aiService;
    private final DashboardCache cache;

    public DashboardService(ApplicationRepository applications, ApplicationEventRepository appEvents,
                            InterviewSessionRepository interviews, ResumeService resumes, JobRepository jobs,
                            JobMatchRepository matches, AgentRunRepository runs, DashboardRepository dashboard,
                            AiServiceClient aiService, DashboardCache cache) {
        this.applications = applications;
        this.appEvents = appEvents;
        this.interviews = interviews;
        this.resumes = resumes;
        this.jobs = jobs;
        this.matches = matches;
        this.runs = runs;
        this.dashboard = dashboard;
        this.aiService = aiService;
        this.cache = cache;
    }

    /**
     * The cached read of the dashboard (Epic 125): a hit answers from the cache; the
     * miss builds (below), stores, and answers. Sits outside the transaction on
     * purpose -- the cache is not the database's concern, and a TTL'd stale read is a
     * documented trade, never a correctness one.
     */
    public DashboardResponse build(UUID userId) {
        var cached = cache.get(userId);
        if (cached.isPresent()) {
            return cached.get();
        }
        DashboardResponse built = buildUncached(userId);
        cache.put(userId, built);
        return built;
    }

    @Transactional(readOnly = true)
    DashboardResponse buildUncached(UUID userId) {
        return new DashboardResponse(
                kanban(userId),
                interviews.countByUserId(userId),
                dashboard.averageMatch(userId),
                dashboard.needsAttention(userId, STALE_DAYS),
                dashboard.attention(userId, STALE_DAYS, ATTENTION_LIMIT),
                followUps(userId),
                currentResume(userId),
                skillGaps(userId),
                recommendedJobs(userId),
                recentRuns(userId),
                recentActivity(userId));
    }

    /**
     * The recommended list (Epic 186): the SQL answers a wider pool ordered by the
     * computed match; rows the reader never scored — the null-overall tail — are
     * ranked here by the deterministic skill-overlap score, and {@link TopK} keeps
     * the strongest of them to fill the window. A matched row keeps its SQL order:
     * the computed match is the authority, the overlap score is only the order of
     * the rows the engine has not measured yet.
     */
    private List<RecommendedJob> recommendedJobs(UUID userId) {
        List<RecommendedJob> pool = dashboard.recommendedJobs(userId, RECOMMENDED_LIMIT * 4);
        if (pool.size() <= RECOMMENDED_LIMIT) {
            return pool;
        }
        List<RecommendedJob> matched = new java.util.ArrayList<>();
        List<RecommendedJob> unmatched = new java.util.ArrayList<>();
        for (RecommendedJob job : pool) {
            (job.matchOverall() != null ? matched : unmatched).add(job);
        }
        if (unmatched.size() > RECOMMENDED_LIMIT) {
            String readerSkills = resumeSkillText(userId);
            RecommendedJob[] ranked = unmatched.toArray(RecommendedJob[]::new);
            int[] kept = TopK.select(ranked, RECOMMENDED_LIMIT,
                    job -> Recommendation.score(readerSkills, job.skills(), 0, 0));
            List<RecommendedJob> best = new java.util.ArrayList<>();
            for (int index : kept) {
                best.add(ranked[index]);
            }
            unmatched = best;
        }
        List<RecommendedJob> out = new java.util.ArrayList<>(matched);
        out.addAll(unmatched);
        return out.subList(0, Math.min(RECOMMENDED_LIMIT, out.size()));
    }

    /** The reader's current skills as one comma-joined string, or "" when there is no resume. */
    private String resumeSkillText(UUID userId) {
        return resumes.currentResumeWithVersion(userId)
                .flatMap(r -> r.getCurrentVersionId() == null
                        ? java.util.Optional.<UUID>empty()
                        : java.util.Optional.of(r.getCurrentVersionId()))
                .map(resumes::versionSkills)
                .map(items -> items.stream()
                        .map(com.careeros.resume.dto.ResumeDtos.SkillItem::name)
                        .collect(java.util.stream.Collectors.joining(", ")))
                .orElse("");
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
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> gaps = best.getSkillGaps().stream()
                .filter(g -> g instanceof Map)
                .map(g -> (Map<String, Object>) g)
                .toList();
        return new SkillGapDigest(best.getJobId(), jobTitle, best.getOverall(),
                best.getMissingSkills(), best.getMatchedSkills(), gaps);
    }

    private List<RecentRun> recentRuns(UUID userId) {
        var page = runs.findRecent(userId, null, Paging.first(RECENT_LIMIT));
        return page != null ? page.stream().map(DashboardService::toRun).toList() : List.of();
    }

    private List<RecentActivity> recentActivity(UUID userId) {
        return appEvents.findByUserIdOrderByCreatedAtDesc(userId, Paging.first(RECENT_LIMIT)).stream()
                .map(DashboardService::toActivity).toList();
    }

    /**
     * Follow-up reminders for the dashboard tile (11.3). The ai-service ranks contacts
     * by their relation's cadence and drafts a message for each; this method forwards
     * the rows and owns none of the logic. A failure here degrades the tile to empty,
     * never the whole dashboard.
     */
    private List<FollowUpItem> followUps(UUID userId) {
        try {
            return aiService.followUps(userId).stream()
                    .map(DashboardService::toFollowUp)
                    .toList();
        } catch (Exception e) {
            return List.of();
        }
    }

    private static FollowUpItem toFollowUp(Map<String, Object> row) {
        return new FollowUpItem(
                UUID.fromString(String.valueOf(row.get("id"))),
                String.valueOf(row.get("name")),
                row.get("company") != null ? String.valueOf(row.get("company")) : null,
                row.get("relation") != null ? String.valueOf(row.get("relation")) : null,
                row.get("priority") != null ? String.valueOf(row.get("priority")) : null,
                row.get("days_since") instanceof Number n ? n.intValue() : null,
                row.get("cadence_days") instanceof Number n ? n.intValue() : null,
                row.get("suggested_message") != null ? String.valueOf(row.get("suggested_message")) : null);
    }

    private static RecentRun toRun(AgentRun r) {
        return new RecentRun(r.getId(), r.getAgent(), r.getTrigger(), r.getStatus(), r.getModel(),
                r.getInputTokens(), r.getOutputTokens(), r.getCostUsd(), r.getStartedAt(), r.getFinishedAt());
    }

    private static RecentActivity toActivity(ApplicationEvent e) {
        return new RecentActivity(e.getId(), e.getApplicationId(), e.getKind(), e.getPayload(), e.getCreatedAt());
    }
}
