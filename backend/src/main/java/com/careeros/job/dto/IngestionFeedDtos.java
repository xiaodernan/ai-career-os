package com.careeros.job.dto;

import com.careeros.job.entity.IngestionFeed;
import com.careeros.job.entity.IngestionRun;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import java.time.OffsetDateTime;
import java.util.Map;
import java.util.UUID;

/**
 * The scheduled-ingestion wire shapes (roadmap 19.2).
 *
 * <p>A feed is a URL plus the label its postings carry. The runner's answer is the run
 * itself: a failed pull is a 200 with {@code status: "failed"} and the reason, because
 * "the feed is down" is an outcome the reader asked to see, not an error in the request.
 */
public final class IngestionFeedDtos {

    public record FeedRequest(
            @NotBlank @Size(max = 120) String name,
            @NotBlank @Size(max = 2048) String url,
            @Size(max = 40) String source) {
    }

    /** The one switch a feed has: whether the night's sweep includes it. */
    public record FeedPatch(@NotNull Boolean enabled) {
    }

    public record RunItem(
            UUID id,
            UUID feedId,
            String feedName,
            String status,
            String error,
            Map<String, Object> counts,
            OffsetDateTime startedAt,
            OffsetDateTime finishedAt,
            OffsetDateTime appliedAt,
            Map<String, Object> appliedCounts) {

        public static RunItem of(IngestionRun run, String feedName) {
            return new RunItem(run.getId(), run.getFeedId(), feedName, run.getStatus(),
                    run.getError(), run.getCounts(), run.getStartedAt(), run.getFinishedAt(),
                    run.getAppliedAt(), run.getAppliedCounts());
        }
    }

    /**
     * What an apply wrote, counted by outcome. The run's {@code counts} say what the engine
     * proposed; these say what the board received, and a posting the plan proposed as a
     * create that the board already had is not one of them.
     */
    public record ApplyResult(
            int created, int updated, int closed, OffsetDateTime appliedAt) {
    }

    public record FeedItem(
            UUID id,
            String name,
            String url,
            String source,
            boolean enabled,
            OffsetDateTime createdAt,
            RunItem lastRun) {

        public static FeedItem of(IngestionFeed feed, RunItem lastRun) {
            return new FeedItem(feed.getId(), feed.getName(), feed.getUrl(), feed.getSource(),
                    feed.isEnabled(), feed.getCreatedAt(), lastRun);
        }
    }

    /** A run plus the engine's plan -- the detail read, kept out of the list rows. */
    public record RunDetail(RunItem run, Map<String, Object> plan) {
    }

    private IngestionFeedDtos() {
    }
}
