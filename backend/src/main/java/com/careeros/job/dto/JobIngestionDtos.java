package com.careeros.job.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.Size;
import java.util.List;
import java.util.Map;

/**
 * The job-ingestion wire shapes (14.2-14.3).
 *
 * <p>Postings are free-form because a connector's payload is: the ai-service
 * normalizes it onto the canonical `jobs` fields. Keeping them as `Map`s here
 * means a new source does not need a new Java type before it can be swept.
 */
public final class JobIngestionDtos {

    private JobIngestionDtos() {
    }

    /**
     * 14.2 -- the feed to parse: RSS 2.0 / Atom XML, or a board-API JSON payload.
     */
    public record ParseFeedRequest(
            @NotBlank @Size(max = 5_000_000) String feed,
            @Size(max = 40) String source) {
    }

    /**
     * 14.3 -- the batch to deduplicate. The fingerprint is computed by the
     * engine, so the client sends postings exactly as the source carried them.
     */
    public record DedupeRequest(List<Map<String, Object>> postings) {
    }

    /**
     * 14.3 -- the corpus to sweep. The windows are the user's: a board that
     * refreshes weekly wants a different age cap than one that posts daily.
     */
    public record FreshnessSweepRequest(List<Map<String, Object>> postings,
                                         @Positive Integer maxAgeDays,
                                         @Positive Integer staleSeenDays) {
    }

    /**
     * 14.3 -- one sweep plan. `existing` is the corpus already in `jobs`, so the
     * plan can tell a new posting from one that is already known and should be
     * refreshed instead of duplicated.
     */
    public record PlanIngestRequest(
            @Size(max = 5_000_000) String feed,
            @Size(max = 40) String source,
            List<Map<String, Object>> existing,
            @Positive Integer maxAgeDays,
            @Positive Integer staleSeenDays) {
    }
}
