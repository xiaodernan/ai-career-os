package com.careeros.job.service;

import com.careeros.ai.AiServiceClient;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.common.Paging;
import com.careeros.job.dto.IngestionFeedDtos.FeedItem;
import com.careeros.job.dto.IngestionFeedDtos.FeedRequest;
import com.careeros.job.dto.IngestionFeedDtos.RunDetail;
import com.careeros.job.dto.IngestionFeedDtos.RunItem;
import com.careeros.job.entity.Company;
import com.careeros.job.entity.IngestionFeed;
import com.careeros.job.entity.IngestionRun;
import com.careeros.job.entity.Job;
import com.careeros.job.repository.CompanyRepository;
import com.careeros.job.repository.IngestionFeedRepository;
import com.careeros.job.repository.IngestionRunRepository;
import com.careeros.job.repository.JobRepository;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * The nightly sweep and the feeds it sweeps (roadmap 19.2).
 *
 * <p>One pull is: fetch the feed over HTTP, hand the body and the open corpus to the
 * plan engine (14.3), and file the plan as a run. The engine's answer is the record;
 * applying a plan to the corpus is a separate, reviewable step, so a night can never
 * rewrite the board as a side effect of reading a feed.
 *
 * <p>A failed pull is a run with {@code status: "failed"} and the sentence that says
 * why -- the night is not silent, and one dead feed does not stop the others. Runs are
 * written when the pull ends, so a process that dies mid-fetch leaves no row claiming to
 * still be running.
 */
@Service
public class ScheduledIngestionService {

    private static final Logger log = LoggerFactory.getLogger(ScheduledIngestionService.class);

    /** A user's own list, bounded so the night's work is bounded with it. */
    static final int MAX_FEEDS_PER_USER = 20;
    /** How much of the open corpus the planner gets to compare against. */
    static final int CORPUS_LIMIT = 500;
    static final int RUN_LIMIT = 20;
    static final int RUN_LIMIT_MAX = 50;
    private static final int MAX_AGE_DAYS = 60;
    private static final int STALE_SEEN_DAYS = 30;
    private static final int ERROR_LIMIT = 2000;

    private final IngestionFeedRepository feeds;
    private final IngestionRunRepository runs;
    private final JobRepository jobs;
    private final CompanyRepository companies;
    private final FeedFetcher fetcher;
    private final AiServiceClient ai;

    public ScheduledIngestionService(IngestionFeedRepository feeds, IngestionRunRepository runs,
                                     JobRepository jobs, CompanyRepository companies,
                                     FeedFetcher fetcher, AiServiceClient ai) {
        this.feeds = feeds;
        this.runs = runs;
        this.jobs = jobs;
        this.companies = companies;
        this.fetcher = fetcher;
        this.ai = ai;
    }

    @Transactional(readOnly = true)
    public List<FeedItem> listFeeds(UUID userId) {
        return feeds.findByUserIdOrderByCreatedAtDesc(userId).stream()
                .map(feed -> FeedItem.of(feed, lastRun(feed)))
                .toList();
    }

    @Transactional
    public FeedItem createFeed(UUID userId, FeedRequest request) {
        String url = request.url().trim();
        if (!FeedUrls.isHttpUrl(url)) {
            throw new ApiException(ApiErrorCode.VALIDATION_STRUCTURE_INVALID,
                    "A feed URL must be an absolute http(s) address");
        }
        if (feeds.countByUserId(userId) >= MAX_FEEDS_PER_USER) {
            throw new ApiException(ApiErrorCode.VALIDATION_STRUCTURE_INVALID,
                    "A user can keep at most " + MAX_FEEDS_PER_USER + " feeds");
        }
        IngestionFeed feed = new IngestionFeed();
        feed.setUserId(userId);
        feed.setName(request.name().trim());
        feed.setUrl(url);
        feed.setSource(sourceLabel(request.source()));
        feed.setEnabled(true);
        return FeedItem.of(feeds.save(feed), null);
    }

    @Transactional
    public FeedItem setEnabled(UUID userId, UUID feedId, boolean enabled) {
        IngestionFeed feed = requireFeed(userId, feedId);
        feed.setEnabled(enabled);
        IngestionFeed saved = feeds.save(feed);
        return FeedItem.of(saved, lastRun(saved));
    }

    @Transactional
    public void deleteFeed(UUID userId, UUID feedId) {
        feeds.delete(requireFeed(userId, feedId));
    }

    /** Pulls one feed now and answers with the run (and its plan). */
    public RunDetail runNow(UUID userId, UUID feedId) {
        return runFeed(requireFeed(userId, feedId));
    }

    /**
     * The night's sweep: every enabled feed, one after another. A feed that fails is
     * that feed's failed run; the loop goes on, and the count answers how many were due.
     */
    public int sweepEnabled() {
        List<IngestionFeed> due = feeds.findByEnabledTrueOrderByCreatedAtAsc();
        for (IngestionFeed feed : due) {
            try {
                runFeed(feed);
            } catch (RuntimeException e) {
                // runFeed already records fetch/plan failures; only a filing failure
                // reaches here, and it must not take the rest of the night down.
                log.warn("scheduled ingestion could not file the run for feed {}", feed.getId(), e);
            }
        }
        return due.size();
    }

    @Transactional(readOnly = true)
    public List<RunItem> listRuns(UUID userId, int limit) {
        int size = Math.max(1, Math.min(limit, RUN_LIMIT_MAX));
        Map<UUID, String> names = feeds.findByUserIdOrderByCreatedAtDesc(userId).stream()
                .collect(Collectors.toMap(IngestionFeed::getId, IngestionFeed::getName));
        return runs.findByUserIdOrderByStartedAtDesc(userId, Paging.first(size)).stream()
                .map(run -> RunItem.of(run, names.getOrDefault(run.getFeedId(), "")))
                .toList();
    }

    @Transactional(readOnly = true)
    public RunDetail runDetail(UUID userId, UUID runId) {
        IngestionRun run = runs.findByIdAndUserId(runId, userId)
                .orElseThrow(() -> new ApiException(ApiErrorCode.INGESTION_RUN_NOT_FOUND,
                        "Ingestion run not found"));
        String name = feeds.findById(run.getFeedId()).map(IngestionFeed::getName).orElse("");
        return new RunDetail(RunItem.of(run, name), run.getPlan());
    }

    /**
     * One pull. The plan is the engine's, the fetch is bounded by {@link HttpFeedFetcher},
     * and every failure becomes this run's {@code error} rather than an exception the
     * scheduler would have to catch.
     */
    RunDetail runFeed(IngestionFeed feed) {
        OffsetDateTime startedAt = OffsetDateTime.now();
        IngestionRun run = new IngestionRun();
        run.setUserId(feed.getUserId());
        run.setFeedId(feed.getId());
        run.setStartedAt(startedAt);
        Map<String, Object> plan = null;
        try {
            String body = fetcher.fetch(feed.getUrl());
            plan = ai.planIngest(body, feed.getSource(), openCorpus(), MAX_AGE_DAYS,
                    STALE_SEEN_DAYS, feed.getUserId());
            run.setStatus(IngestionRun.STATUS_COMPLETED);
            run.setPlan(plan);
            run.setCounts(countsOf(plan));
        } catch (RuntimeException e) {
            run.setStatus(IngestionRun.STATUS_FAILED);
            run.setError(clip(e.getMessage()));
        }
        run.setFinishedAt(OffsetDateTime.now());
        IngestionRun saved = runs.save(run);
        return new RunDetail(RunItem.of(saved, feed.getName()), plan);
    }

    /**
     * The open corpus in the shape the engine fingerprints: id, company name, title,
     * location, and the row's own discovery time as `posted_at`. Jobs carry no per-posting
     * date, so age means "how long this row has been on the board", which is exactly what
     * the close rule needs -- an expired row that did not reappear tonight.
     */
    private List<Map<String, Object>> openCorpus() {
        List<Job> open = newestOpenJobs();
        Map<UUID, String> names = companies
                .findAllById(open.stream().map(Job::getCompanyId).distinct().toList()).stream()
                .collect(Collectors.toMap(Company::getId, Company::getName));
        return open.stream().map(job -> {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("id", job.getId().toString());
            row.put("company", names.getOrDefault(job.getCompanyId(), ""));
            row.put("title", job.getTitle());
            row.put("location", job.getLocation());
            row.put("posted_at", job.getPostedAt() == null ? null : job.getPostedAt().toString());
            return row;
        }).toList();
    }

    /**
     * The newest open rows, window by window through {@link Paging} — the corpus limit is
     * larger than one page, and a window is built by the one class allowed to build one.
     */
    private List<Job> newestOpenJobs() {
        List<Job> open = new ArrayList<>();
        Sort newestFirst = Sort.by(Sort.Direction.DESC, "postedAt");
        for (int page = 0; open.size() < CORPUS_LIMIT; page += 1) {
            int size = Math.min(Paging.MAX_PAGE_SIZE, CORPUS_LIMIT - open.size());
            Page<Job> window = jobs.findByStatus("open",
                    Paging.of(page, size).pageable().withSort(newestFirst));
            open.addAll(window.getContent());
            if (!window.hasNext() || window.getContent().isEmpty()) break;
        }
        return open;
    }

    private RunItem lastRun(IngestionFeed feed) {
        return runs.findFirstByFeedIdOrderByStartedAtDesc(feed.getId())
                .map(run -> RunItem.of(run, feed.getName()))
                .orElse(null);
    }

    private IngestionFeed requireFeed(UUID userId, UUID feedId) {
        return feeds.findByIdAndUserId(feedId, userId)
                .orElseThrow(() -> new ApiException(ApiErrorCode.INGESTION_FEED_NOT_FOUND,
                        "Feed not found"));
    }

    private static String sourceLabel(String raw) {
        String source = raw == null ? "" : raw.trim();
        return source.isEmpty() ? "feed" : source;
    }

    private static Map<String, Object> countsOf(Map<String, Object> plan) {
        if (plan == null || !(plan.get("counts") instanceof Map<?, ?> raw)) {
            return Map.of();
        }
        Map<String, Object> out = new LinkedHashMap<>();
        raw.forEach((key, value) -> out.put(String.valueOf(key), value));
        return out;
    }

    private static String clip(String message) {
        String text = message == null || message.isBlank() ? "the pull failed without a reason" : message;
        return text.length() <= ERROR_LIMIT ? text : text.substring(0, ERROR_LIMIT);
    }
}
