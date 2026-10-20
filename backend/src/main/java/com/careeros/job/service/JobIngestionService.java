package com.careeros.job.service;

import com.careeros.ai.AiServiceClient;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Job ingestion (14.2-14.3): fetch, parse, dedupe, and sweep jobs from external sources.
 *
 * <p>The ai-service composes the ingestion plan; this service forwards the calls and
 * owns none of the logic. Every route is user-scoped by the ai-service's own
 * {@code X-User-Id} header.
 */
@Service
public class JobIngestionService {

    /** The engine's own defaults, used when the caller names no window. */
    private static final int DEFAULT_MAX_AGE_DAYS = 60;
    private static final int DEFAULT_STALE_SEEN_DAYS = 30;

    private final AiServiceClient aiService;

    public JobIngestionService(AiServiceClient aiService) {
        this.aiService = aiService;
    }

    /**
     * Parse a feed (RSS/Atom XML or board-API JSON) into raw postings (14.2).
     * The parse is deterministic and offline-testable; the fetch stays in the backend.
     */
    @Transactional(readOnly = true)
    public Map<String, Object> parseFeed(UUID userId, String feed, String source) {
        return aiService.parseFeed(feed, source, userId);
    }

    /**
     * Deduplicate postings against the existing corpus (14.3).
     * Exact-fingerprint duplicates collapse to the newest / most complete survivor.
     */
    @Transactional(readOnly = true)
    public Map<String, Object> dedupeJobs(UUID userId, List<Map<String, Object>> postings) {
        return aiService.dedupeJobs(postings, userId);
    }

    /**
     * Freshness sweep: partition postings into fresh / stale / expired / undated (14.3).
     */
    @Transactional(readOnly = true)
    public Map<String, Object> freshnessSweep(UUID userId, List<Map<String, Object>> postings,
                                               Integer maxAgeDays, Integer staleSeenDays) {
        return aiService.freshnessSweep(postings,
                maxAgeDays == null ? DEFAULT_MAX_AGE_DAYS : maxAgeDays,
                staleSeenDays == null ? DEFAULT_STALE_SEEN_DAYS : staleSeenDays, userId);
    }

    /**
     * One plan for a sweep: create / update / close + within-batch duplicates (14.3).
     */
    @Transactional(readOnly = true)
    public Map<String, Object> planIngest(UUID userId, String feed, String source,
                                          List<Map<String, Object>> existing,
                                          Integer maxAgeDays, Integer staleSeenDays) {
        return aiService.planIngest(feed, source == null || source.isBlank() ? "rss" : source, existing,
                maxAgeDays == null ? DEFAULT_MAX_AGE_DAYS : maxAgeDays,
                staleSeenDays == null ? DEFAULT_STALE_SEEN_DAYS : staleSeenDays, userId);
    }
}
