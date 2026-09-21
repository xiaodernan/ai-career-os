package com.careeros.report.dto;

import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/** Payload for GET /api/v1/reports/dashboard. */
public final class DashboardDtos {

    private DashboardDtos() {
    }

    public record Kanban(Map<String, Long> statusCounts, long total, long offers) {
    }

    public record ResumeSummary(UUID resumeId, UUID versionId, String title, String status,
                                Map<String, Object> score) {
    }

    public record SkillGapDigest(UUID jobId, String jobTitle, Float overall,
                                 List<Object> missingSkills, List<Object> matchedSkills) {
    }

    public record RecommendedJob(UUID id, String title, String companyName, String location,
                                 String remoteType, OffsetDateTime postedAt, Float matchOverall,
                                 UUID matchId) {
    }

    public record RecentRun(UUID id, String agent, String trigger, String status, String model,
                            Integer inputTokens, Integer outputTokens, BigDecimal costUsd,
                            OffsetDateTime startedAt, OffsetDateTime finishedAt) {
    }

    public record RecentActivity(UUID id, UUID applicationId, String kind, Map<String, Object> payload,
                                 OffsetDateTime createdAt) {
    }

    public record DashboardResponse(Kanban kanban,
                                    long interviews,
                                    ResumeSummary currentResume,
                                    SkillGapDigest skillGaps,
                                    List<RecommendedJob> recommendedJobs,
                                    List<RecentRun> recentRuns,
                                    List<RecentActivity> recentActivity) {
    }
}
