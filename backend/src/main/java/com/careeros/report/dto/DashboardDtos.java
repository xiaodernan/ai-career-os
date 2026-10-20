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
                                 List<Object> missingSkills, List<Object> matchedSkills,
                                 List<Map<String, Object>> gaps) {
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

    /**
     * One open application waiting on the user, and why it is listed.
     *
     * `reason` is the query's own classification rather than a second guess at the backend:
     * `reminder_due` means the user asked to be told at this time, `stale` means nobody has
     * logged a step on it for the window. The frontend renders the two differently, so a reason
     * the backend stopped sending would show up as an unlabelled row rather than as a wrong one.
     */
    public record AttentionItem(UUID id, String title, String companyName, String status,
                                String reason, OffsetDateTime reminderAt,
                                OffsetDateTime updatedAt) {
    }

    /**
     * One contact needing a follow-up, ranked by its relation's cadence. The draft
     * message is the ai-service's own, so the tile never invents text the engine did
     * not produce.
     */
    public record FollowUpItem(UUID id, String name, String company, String relation,
                               String priority, Integer daysSince, Integer cadenceDays,
                               String suggestedMessage) {
    }

    /**
     * `avgMatch` is the mean of the newest match per scored job (0..1) and null when nothing has
     * been scored; `needsAttention` counts open applications that are waiting on the user, and
     * `attention` is the rows behind that count -- same predicate, so the strip cannot say three
     * while the card lists two. The stat strip hides the match ring on a null average rather than
     * drawing a zero-scored resume.
     */
    public record DashboardResponse(Kanban kanban,
                                    long interviews,
                                    Float avgMatch,
                                    long needsAttention,
                                    List<AttentionItem> attention,
                                    List<FollowUpItem> followUps,
                                    ResumeSummary currentResume,
                                    SkillGapDigest skillGaps,
                                    List<RecommendedJob> recommendedJobs,
                                    List<RecentRun> recentRuns,
                                    List<RecentActivity> recentActivity) {
    }
}
