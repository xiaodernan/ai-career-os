package com.careeros.job.web;

import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import com.careeros.job.dto.JobIngestionDtos.DedupeRequest;
import com.careeros.job.dto.JobIngestionDtos.FreshnessSweepRequest;
import com.careeros.job.dto.JobIngestionDtos.ParseFeedRequest;
import com.careeros.job.dto.JobIngestionDtos.PlanIngestRequest;
import com.careeros.job.service.JobIngestionService;
import jakarta.validation.Valid;
import java.util.Map;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Job ingestion (14.2-14.3): fetch, parse, dedupe, and sweep jobs from external sources.
 *
 * <p>The ai-service composes the ingestion plan; this controller forwards the calls
 * and owns none of the logic. Every route is user-scoped by the ai-service's own
 * {@code X-User-Id} header.
 */
@RestController
@RequestMapping("/api/v1/jobs/ingest")
public class JobIngestionController {

    private final JobIngestionService ingestion;

    public JobIngestionController(JobIngestionService ingestion) {
        this.ingestion = ingestion;
    }

    /**
     * 14.2 -- parse a feed (RSS/Atom XML or board-API JSON) into raw postings.
     * The parse is deterministic and offline-testable; the fetch stays in the backend.
     */
    @PostMapping("/parse")
    public Map<String, Object> parseFeed(@CurrentUser AuthUser user,
                                          @RequestBody @Valid ParseFeedRequest request) {
        return ingestion.parseFeed(user.id(), request.feed(), request.source());
    }

    /**
     * 14.3 -- deduplicate postings against the existing corpus.
     * Exact-fingerprint duplicates collapse to the newest / most complete survivor.
     */
    @PostMapping("/dedupe")
    public Map<String, Object> dedupeJobs(@CurrentUser AuthUser user,
                                           @RequestBody @Valid DedupeRequest request) {
        return ingestion.dedupeJobs(user.id(), request.postings());
    }

    /**
     * 14.3 -- freshness sweep: partition postings into fresh / stale / expired / undated.
     */
    @PostMapping("/freshness-sweep")
    public Map<String, Object> freshnessSweep(@CurrentUser AuthUser user,
                                                @RequestBody @Valid FreshnessSweepRequest request) {
        return ingestion.freshnessSweep(user.id(), request.postings(),
                request.maxAgeDays(), request.staleSeenDays());
    }

    /**
     * 14.3 -- one plan for a sweep: create / update / close + within-batch duplicates.
     */
    @PostMapping("/plan")
    public Map<String, Object> planIngest(@CurrentUser AuthUser user,
                                           @RequestBody @Valid PlanIngestRequest request) {
        return ingestion.planIngest(user.id(), request.feed(), request.source(), request.existing(),
                request.maxAgeDays(), request.staleSeenDays());
    }
}
