package com.careeros.job.service;

import com.careeros.ai.AiServiceClient;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.common.PageDTO;
import com.careeros.common.Paging;
import com.careeros.job.connector.BoardConnector;
import com.careeros.job.connector.BoardConnectors;
import com.careeros.job.dto.IngestionFeedDtos.ApplyResult;
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
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * The nightly sweep and the feeds it sweeps (roadmap 19.2, board connectors 19.8).
 *
 * <p>One pull is: fetch the feed over HTTP, hand the body and the open corpus to the
 * plan engine (14.3), and file the plan as a run. The engine's answer is the record;
 * applying a plan to the corpus is a separate, reviewable step, so a night can never
 * rewrite the board as a side effect of reading a feed. A feed whose {@code source}
 * names a board connector (Greenhouse, Lever) is addressed by the connector -- a token
 * or a board page becomes the API URL -- and its name becomes the company its rows
 * carry, something neither board's payload says in a posting.
 *
 * <p>A failed pull is a run with {@code status: "failed"} and the sentence that says
 * why -- the night is not silent, and one dead feed does not stop the others. Runs are
 * written when the pull ends, so a process that dies mid-fetch leaves no row claiming to
 * still be running.
 *
 * <p>Each run that ends is also a reading: {@link IngestionMetrics} takes the outcome and
 * the moment it finished, so "did the night succeed" is a scrape rather than a log search.
 *
 * <p>A plan is still only a proposal until someone applies it ({@link #applyRun}). The
 * write is the reader's step, not the sweep's: the night may have misread a feed, and a
 * board that rewrote itself every morning would have no moment for that judgment. The
 * apply is once per run and counted on the run itself, so pressing the button twice is a
 * refusal rather than a second copy of every posting.
 */
@Service
public class ScheduledIngestionService {

    private static final Logger log = LoggerFactory.getLogger(ScheduledIngestionService.class);

    /** A user's own list, bounded so the night's work is bounded with it. */
    static final int MAX_FEEDS_PER_USER = 20;
    /** How much of the open corpus the planner gets to compare against. */
    static final int CORPUS_LIMIT = 500;
    private static final int MAX_AGE_DAYS = 60;
    private static final int STALE_SEEN_DAYS = 30;
    private static final int ERROR_LIMIT = 2000;

    private final IngestionFeedRepository feeds;
    private final IngestionRunRepository runs;
    private final JobRepository jobs;
    private final CompanyRepository companies;
    private final FeedFetcher fetcher;
    private final BoardConnectors connectors;
    private final AiServiceClient ai;
    private final IngestionMetrics metrics;

    public ScheduledIngestionService(IngestionFeedRepository feeds, IngestionRunRepository runs,
                                     JobRepository jobs, CompanyRepository companies,
                                     FeedFetcher fetcher, BoardConnectors connectors,
                                     AiServiceClient ai, IngestionMetrics metrics) {
        this.feeds = feeds;
        this.runs = runs;
        this.jobs = jobs;
        this.companies = companies;
        this.fetcher = fetcher;
        this.connectors = connectors;
        this.ai = ai;
        this.metrics = metrics;
    }

    @Transactional(readOnly = true)
    public List<FeedItem> listFeeds(UUID userId) {
        return feeds.findByUserIdOrderByCreatedAtDesc(userId).stream()
                .map(feed -> FeedItem.of(feed, lastRun(feed)))
                .toList();
    }

    @Transactional
    public FeedItem createFeed(UUID userId, FeedRequest request) {
        String input = request.url().trim();
        BoardConnector connector = connectors.forSource(request.source()).orElse(null);
        String url;
        String source;
        if (connector == null) {
            if (!FeedUrls.isHttpUrl(input)) {
                throw new ApiException(ApiErrorCode.FEED_URL_INVALID,
                        "A feed URL must be an absolute http(s) address");
            }
            url = input;
            source = sourceLabel(request.source());
        } else {
            // the connector is what knows a board address when it sees one, so its
            // refusal -- the sentence naming what would work -- is the registration's
            url = boardUrl(connector, input);
            source = connector.source();
        }
        if (feeds.countByUserId(userId) >= MAX_FEEDS_PER_USER) {
            throw new ApiException(ApiErrorCode.FEED_LIMIT_REACHED,
                    "A user can keep at most " + MAX_FEEDS_PER_USER + " feeds");
        }
        IngestionFeed feed = new IngestionFeed();
        feed.setUserId(userId);
        feed.setName(request.name().trim());
        feed.setUrl(url);
        feed.setSource(source);
        feed.setEnabled(true);
        return FeedItem.of(feeds.save(feed), null);
    }

    private static String boardUrl(BoardConnector connector, String input) {
        try {
            return connector.apiUrl(input);
        } catch (IllegalArgumentException e) {
            // the connector's own sentence is the precise one, but a board is one
            // meaning to the reader -- the wire carries the sentence the browser can
            // translate for every board instead
            throw new ApiException(ApiErrorCode.FEED_BOARD_INVALID,
                    "A board feed takes the board's token, its page address, or the board's API URL");
        }
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

    /**
     * The run history as a page, like every other list board: the window is the
     * caller's page/size (clamped by {@link Paging}), and the answer carries the
     * total so the screen can page past the first window.
     */
    @Transactional(readOnly = true)
    public PageDTO<RunItem> listRuns(UUID userId, int page, int size) {
        Map<UUID, String> names = feeds.findByUserIdOrderByCreatedAtDesc(userId).stream()
                .collect(Collectors.toMap(IngestionFeed::getId, IngestionFeed::getName));
        return PageDTO.from(
                runs.findByUserIdOrderByStartedAtDescIdDesc(userId, Paging.of(page, size).pageable()),
                run -> RunItem.of(run, names.getOrDefault(run.getFeedId(), "")));
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
     * Writes a completed run's plan to the board, once.
     *
     * <p>The board is global, and an apply writes the rows the plan named: a create becomes
     * a company (by name, reused when it exists) and an open job, an update refreshes the
     * row the engine matched, and a close closes the job the freshness sweep named. The
     * plan's rows carry no posting date -- the board's age has always meant "how long this
     * row has been here", so the job's own creation timestamp keeps that meaning. A row
     * whose title is empty is not a posting and is not counted.
     *
     * <p>The run is locked for the transaction and stamped with {@code applied_at} and the
     * counts actually written, so two presses cannot write the plan twice. A failed run
     * has no plan and is refused; the receipt is read back through the run list.
     */
    @Transactional
    public ApplyResult applyRun(UUID userId, UUID runId) {
        IngestionRun run = runs.findWithLockByIdAndUserId(runId, userId)
                .orElseThrow(() -> new ApiException(ApiErrorCode.INGESTION_RUN_NOT_FOUND,
                        "Ingestion run not found"));
        if (run.getAppliedAt() != null) {
            throw new ApiException(ApiErrorCode.INGESTION_RUN_ALREADY_APPLIED,
                    "This run's plan was already applied");
        }
        if (!IngestionRun.STATUS_COMPLETED.equals(run.getStatus()) || run.getPlan() == null) {
            throw new ApiException(ApiErrorCode.INGESTION_RUN_NOT_APPLICABLE,
                    "A failed run has no plan to apply");
        }
        IngestionFeed feed = feeds.findById(run.getFeedId())
                .orElseThrow(() -> new IllegalStateException("run " + runId + " outlived its feed"));

        int created = 0;
        int updated = 0;
        int closed = 0;
        for (Map<String, Object> row : rowsOf(run.getPlan(), "create")) {
            if (createJob(row, feed) != null) {
                created += 1;
            }
        }
        for (Map<String, Object> row : rowsOf(run.getPlan(), "update")) {
            int outcome = refreshJob(row, feed);
            if (outcome == CREATED) {
                created += 1;
            } else if (outcome == UPDATED) {
                updated += 1;
            }
        }
        for (Map<String, Object> row : rowsOf(run.getPlan(), "close")) {
            if (closeJob(row)) {
                closed += 1;
            }
        }
        OffsetDateTime appliedAt = OffsetDateTime.now();
        Map<String, Object> appliedCounts = new LinkedHashMap<>();
        appliedCounts.put("created", created);
        appliedCounts.put("updated", updated);
        appliedCounts.put("closed", closed);
        run.setAppliedAt(appliedAt);
        run.setAppliedCounts(appliedCounts);
        runs.save(run);
        return new ApplyResult(created, updated, closed, appliedAt);
    }

    /** What a refresh wrote: nothing (the row or its id is gone), an update, or a create. */
    private static final int NOT_WRITTEN = 0;
    private static final int UPDATED = 1;
    private static final int CREATED = 2;

    private Job createJob(Map<String, Object> row, IngestionFeed feed) {
        String title = text(row, "title");
        if (title == null || title.isBlank()) {
            return null;
        }
        Job job = new Job();
        job.setCompanyId(companyId(text(row, "company"), feed.getName()));
        job.setTitle(title);
        job.setLocation(text(row, "location"));
        job.setRemoteType(orDefault(text(row, "remote_type"), "onsite"));
        job.setEmploymentType(orDefault(text(row, "employment_type"), "full_time"));
        job.setSalaryMin(intOrNull(row.get("salary_min")));
        job.setSalaryMax(intOrNull(row.get("salary_max")));
        job.setSalaryCurrency(orDefault(text(row, "salary_currency"), "CNY"));
        job.setDescription(orDefault(text(row, "description"), ""));
        job.setSkills(strings(row.get("skills")));
        job.setExternalUrl(text(row, "external_url"));
        job.setSource(feed.getSource());
        job.setStatus("open");
        return jobs.save(job);
    }

    /**
     * The engine matches an update by fingerprint and carries the row's id as
     * {@code existingId}. A row deleted since the pull is created from tonight's reading
     * instead: the plan saw the posting live, and dropping it would lose a real opening.
     */
    private int refreshJob(Map<String, Object> row, IngestionFeed feed) {
        UUID id = uuidOrNull(row.get("existingId"));
        if (id == null) {
            return NOT_WRITTEN;
        }
        Job job = jobs.findById(id).orElse(null);
        if (job == null) {
            return createJob(row, feed) == null ? NOT_WRITTEN : CREATED;
        }
        job.setTitle(text(row, "title"));
        job.setLocation(text(row, "location"));
        job.setRemoteType(orDefault(text(row, "remote_type"), job.getRemoteType()));
        job.setEmploymentType(orDefault(text(row, "employment_type"), job.getEmploymentType()));
        job.setSalaryMin(intOrNull(row.get("salary_min")));
        job.setSalaryMax(intOrNull(row.get("salary_max")));
        job.setSalaryCurrency(orDefault(text(row, "salary_currency"), job.getSalaryCurrency()));
        job.setDescription(orDefault(text(row, "description"), job.getDescription()));
        job.setSkills(strings(row.get("skills")));
        job.setExternalUrl(text(row, "external_url"));
        // the posting was in tonight's pull, so it is live again even if it closed earlier
        job.setStatus("open");
        jobs.save(job);
        return UPDATED;
    }

    private boolean closeJob(Map<String, Object> row) {
        UUID id = uuidOrNull(row.get("id"));
        if (id == null) {
            return false;
        }
        Job job = jobs.findById(id).orElse(null);
        if (job == null || "closed".equals(job.getStatus())) {
            return false;
        }
        job.setStatus("closed");
        jobs.save(job);
        return true;
    }

    /** The row's company, by name; a posting that names none belongs to the feed's board. */
    private UUID companyId(String name, String fallbackName) {
        String company = name == null || name.isBlank() ? fallbackName : name;
        return companies.findByName(company)
                .map(Company::getId)
                .orElseGet(() -> {
                    Company created = new Company();
                    created.setName(company);
                    return companies.save(created).getId();
                });
    }

    /** The plan's list under one key, as maps -- a section the plan never carried is empty. */
    private static List<Map<String, Object>> rowsOf(Map<String, Object> plan, String key) {
        Object value = plan.get(key);
        List<Map<String, Object>> rows = new ArrayList<>();
        if (value instanceof List<?> list) {
            for (Object item : list) {
                if (item instanceof Map<?, ?> map) {
                    Map<String, Object> row = new LinkedHashMap<>();
                    map.forEach((k, v) -> row.put(String.valueOf(k), v));
                    rows.add(row);
                }
            }
        }
        return rows;
    }

    private static String text(Map<String, Object> row, String key) {
        Object value = row.get(key);
        return value == null ? null : String.valueOf(value);
    }

    private static String orDefault(String value, String fallback) {
        return value == null || value.isBlank() ? fallback : value;
    }

    private static Integer intOrNull(Object value) {
        if (value instanceof Number number) {
            return number.intValue();
        }
        if (value instanceof String string && !string.isBlank()) {
            try {
                return Integer.valueOf(string.trim());
            } catch (NumberFormatException e) {
                return null;
            }
        }
        return null;
    }

    private static List<String> strings(Object value) {
        if (!(value instanceof List<?> list)) {
            return List.of();
        }
        return list.stream().map(String::valueOf).filter(item -> !item.isBlank()).toList();
    }

    private static UUID uuidOrNull(Object value) {
        if (value instanceof UUID id) {
            return id;
        }
        if (value instanceof String string && !string.isBlank()) {
            try {
                return UUID.fromString(string);
            } catch (IllegalArgumentException e) {
                return null;
            }
        }
        return null;
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
            // a board's rows never name their company (19.8); the feed's name is the
            // board's, and the engine lets a row that does name one win over it
            String company = connectors.forSource(feed.getSource()).isPresent()
                    ? feed.getName() : null;
            plan = ai.planIngest(body, feed.getSource(), openCorpus(), MAX_AGE_DAYS,
                    STALE_SEEN_DAYS, feed.getUserId(), company);
            run.setStatus(IngestionRun.STATUS_COMPLETED);
            run.setPlan(plan);
            run.setCounts(countsOf(plan));
        } catch (RuntimeException e) {
            run.setStatus(IngestionRun.STATUS_FAILED);
            run.setError(clip(e.getMessage()));
        }
        run.setFinishedAt(OffsetDateTime.now());
        IngestionRun saved = runs.save(run);
        // the run that ended is also a reading a scrape sees (19.9): a failed pull moves
        // the counter and leaves the success marker where it was
        metrics.record(saved.getStatus(), saved.getFinishedAt());
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
        for (int page = 0; open.size() < CORPUS_LIMIT; page += 1) {
            int size = Math.min(Paging.MAX_PAGE_SIZE, CORPUS_LIMIT - open.size());
            Page<Job> window = jobs.findByStatusOrderByPostedAtDescIdDesc("open",
                    Paging.of(page, size).pageable());
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
