package com.careeros.job.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.argThat;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.isNull;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.ai.AiServiceClient;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.job.connector.BoardConnectors;
import com.careeros.job.connector.GreenhouseConnector;
import com.careeros.job.connector.LeverConnector;
import com.careeros.job.dto.IngestionFeedDtos.ApplyResult;
import com.careeros.job.dto.IngestionFeedDtos.FeedItem;
import com.careeros.job.dto.IngestionFeedDtos.FeedRequest;
import com.careeros.job.dto.IngestionFeedDtos.RunDetail;
import com.careeros.job.entity.Company;
import com.careeros.job.entity.IngestionFeed;
import com.careeros.job.entity.IngestionRun;
import com.careeros.job.entity.Job;
import com.careeros.job.repository.CompanyRepository;
import com.careeros.job.repository.IngestionFeedRepository;
import com.careeros.job.repository.IngestionRunRepository;
import com.careeros.job.repository.JobRepository;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.time.OffsetDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.test.util.ReflectionTestUtils;

/**
 * One pull, as the sweep performs it (roadmap 19.2).
 *
 * <p>Two claims carry the feature. The first is that the plan is the engine's answer and
 * the run is the record of it: the plan is stored as it came back, and the counts are read
 * off that same answer rather than re-counted by the backend, so the run list and the
 * stored plan cannot disagree. The second is that a dead feed is a *failed run*, not an
 * exception the night has to survive: the reader sees the sentence, and the sweep moves on.
 */
class ScheduledIngestionServiceTest {

    private final UUID userId = UUID.randomUUID();
    private final UUID feedId = UUID.randomUUID();
    private final UUID jobId = UUID.randomUUID();
    private final UUID companyId = UUID.randomUUID();

    private IngestionFeedRepository feeds;
    private IngestionRunRepository runs;
    private JobRepository jobs;
    private CompanyRepository companies;
    private FeedFetcher fetcher;
    private BoardConnectors connectors;
    private AiServiceClient ai;
    private SimpleMeterRegistry registry;
    private IngestionMetrics metrics;
    private ScheduledIngestionService service;

    @BeforeEach
    void setUp() {
        feeds = mock(IngestionFeedRepository.class);
        runs = mock(IngestionRunRepository.class);
        jobs = mock(JobRepository.class);
        companies = mock(CompanyRepository.class);
        fetcher = mock(FeedFetcher.class);
        connectors = new BoardConnectors(
                List.of(new GreenhouseConnector(), new LeverConnector()));
        ai = mock(AiServiceClient.class);
        registry = new SimpleMeterRegistry();
        metrics = new IngestionMetrics(registry);
        service = new ScheduledIngestionService(feeds, runs, jobs, companies, fetcher,
                connectors, ai, metrics);
        when(runs.save(any(IngestionRun.class))).thenAnswer(i -> i.getArgument(0));
    }

    private IngestionFeed feed(String name, String url, String source) {
        IngestionFeed feed = new IngestionFeed();
        ReflectionTestUtils.setField(feed, "id", feedId);
        feed.setUserId(userId);
        feed.setName(name);
        feed.setUrl(url);
        feed.setSource(source);
        return feed;
    }

    private IngestionFeed feed() {
        return feed("Hiring board", "https://boards.example.com/rss", "rss");
    }

    private Job openJob() {
        Job job = new Job();
        ReflectionTestUtils.setField(job, "id", jobId);
        ReflectionTestUtils.setField(job, "postedAt",
                OffsetDateTime.parse("2026-09-30T08:00:00Z"));
        job.setCompanyId(companyId);
        job.setTitle("Backend Engineer");
        job.setLocation("Hangzhou");
        return job;
    }

    private Company company() {
        Company company = new Company();
        ReflectionTestUtils.setField(company, "id", companyId);
        company.setName("Acme");
        return company;
    }

    private IngestionRun savedRun() {
        ArgumentCaptor<IngestionRun> cap = ArgumentCaptor.forClass(IngestionRun.class);
        verify(runs).save(cap.capture());
        return cap.getValue();
    }

    @Test
    @SuppressWarnings("unchecked")
    void a_pull_files_the_engines_plan_and_the_counts_it_carried() {
        IngestionFeed feed = feed();
        Map<String, Object> plan = new LinkedHashMap<>(Map.of(
                "counts", new LinkedHashMap<>(Map.of("incoming", 3, "create", 2, "close", 1)),
                "create", List.of(Map.of("title", "Backend Engineer"))));
        when(feeds.findByIdAndUserId(feedId, userId)).thenReturn(Optional.of(feed));
        when(fetcher.fetch(feed.getUrl())).thenReturn("<rss><item/></rss>");
        when(jobs.findByStatusOrderByPostedAtDescIdDesc(eq("open"), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(openJob())));
        when(companies.findAllById(any())).thenReturn(List.of(company()));
        when(ai.planIngest(any(), any(), anyList(), anyInt(), anyInt(), any(), any()))
                .thenReturn(plan);

        RunDetail detail = service.runNow(userId, feedId);

        assertThat(detail.run().status()).isEqualTo(IngestionRun.STATUS_COMPLETED);
        assertThat(detail.run().error()).isNull();
        assertThat(detail.run().feedName()).isEqualTo("Hiring board");
        assertThat(detail.run().counts()).containsEntry("incoming", 3).containsEntry("close", 1);
        assertThat(detail.run().startedAt()).isNotNull();
        assertThat(detail.run().finishedAt()).isNotNull();
        assertThat(detail.plan()).isEqualTo(plan);

        ArgumentCaptor<List<Map<String, Object>>> corpus = ArgumentCaptor.forClass(List.class);
        verify(ai).planIngest(eq("<rss><item/></rss>"), eq("rss"), corpus.capture(),
                eq(60), eq(30), eq(userId), isNull());
        Map<String, Object> row = corpus.getValue().get(0);
        assertThat(row).containsEntry("id", jobId.toString())
                .containsEntry("company", "Acme")
                .containsEntry("title", "Backend Engineer")
                .containsEntry("location", "Hangzhou")
                .containsEntry("posted_at", "2026-09-30T08:00Z");
    }

    @Test
    void a_dead_feed_is_a_failed_run_with_the_sentence_that_says_why() {
        IngestionFeed feed = feed();
        when(feeds.findByIdAndUserId(feedId, userId)).thenReturn(Optional.of(feed));
        when(fetcher.fetch(feed.getUrl())).thenThrow(new IllegalStateException("Feed answered HTTP 503"));

        RunDetail detail = service.runNow(userId, feedId);

        assertThat(detail.run().status()).isEqualTo(IngestionRun.STATUS_FAILED);
        assertThat(detail.run().error()).isEqualTo("Feed answered HTTP 503");
        assertThat(detail.plan()).isNull();
        assertThat(detail.run().counts()).isNull();
        verify(ai, never()).planIngest(any(), any(), anyList(), anyInt(), anyInt(), any(), any());
        assertThat(savedRun().getStatus()).isEqualTo(IngestionRun.STATUS_FAILED);
    }

    @Test
    void a_failure_without_a_sentence_still_says_something() {
        IngestionFeed feed = feed();
        when(feeds.findByIdAndUserId(feedId, userId)).thenReturn(Optional.of(feed));
        when(fetcher.fetch(feed.getUrl())).thenThrow(new IllegalStateException());

        assertThat(service.runNow(userId, feedId).run().error())
                .isEqualTo("the pull failed without a reason");
    }

    @Test
    void a_very_long_failure_is_clipped_rather_than_stored_whole() {
        IngestionFeed feed = feed();
        when(feeds.findByIdAndUserId(feedId, userId)).thenReturn(Optional.of(feed));
        when(fetcher.fetch(feed.getUrl())).thenThrow(new IllegalStateException("x".repeat(5000)));

        assertThat(service.runNow(userId, feedId).run().error()).hasSize(2000);
    }

    @Test
    void another_users_feed_is_a_404_named_for_feeds() {
        when(feeds.findByIdAndUserId(feedId, userId)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.runNow(userId, feedId))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.code()).isEqualTo(ApiErrorCode.INGESTION_FEED_NOT_FOUND));
    }

    @Test
    void a_feed_is_stored_trimmed_and_labelled() {
        when(feeds.countByUserId(userId)).thenReturn(0L);
        when(feeds.save(any(IngestionFeed.class))).thenAnswer(i -> i.getArgument(0));

        FeedItem item = service.createFeed(userId,
                new FeedRequest("  Daily board  ", " https://boards.example.com/rss ", "  "));

        assertThat(item.name()).isEqualTo("Daily board");
        assertThat(item.url()).isEqualTo("https://boards.example.com/rss");
        assertThat(item.source()).isEqualTo("feed");
        assertThat(item.enabled()).isTrue();
        ArgumentCaptor<IngestionFeed> cap = ArgumentCaptor.forClass(IngestionFeed.class);
        verify(feeds).save(cap.capture());
        assertThat(cap.getValue().getUserId()).isEqualTo(userId);
        assertThat(cap.getValue().getSource()).isEqualTo("feed");
    }

    @Test
    void a_feed_url_must_be_absolute_http() {
        assertThatThrownBy(() -> service.createFeed(userId,
                new FeedRequest("Board", "boards.example.com/rss", null)))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.code()).isEqualTo(ApiErrorCode.FEED_URL_INVALID));
        assertThatThrownBy(() -> service.createFeed(userId,
                new FeedRequest("Board", "ftp://boards.example.com/rss", null)))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.code()).isEqualTo(ApiErrorCode.FEED_URL_INVALID));
        verify(feeds, never()).save(any(IngestionFeed.class));
    }

    @Test
    void a_board_token_is_stored_as_the_api_url_it_names() {
        when(feeds.countByUserId(userId)).thenReturn(0L);
        when(feeds.save(any(IngestionFeed.class))).thenAnswer(i -> i.getArgument(0));

        FeedItem item = service.createFeed(userId,
                new FeedRequest("Acme", " acme ", "Greenhouse"));

        assertThat(item.name()).isEqualTo("Acme");
        assertThat(item.url())
                .isEqualTo("https://boards-api.greenhouse.io/v1/boards/acme/jobs?content=true");
        assertThat(item.source()).isEqualTo("greenhouse");  // the connector's own label
    }

    @Test
    void a_board_address_the_connector_cannot_read_is_refused_with_its_sentence() {
        assertThatThrownBy(() -> service.createFeed(userId,
                new FeedRequest("Acme", "https://example.com/acme", "lever")))
                .isInstanceOfSatisfying(ApiException.class, e -> {
                    assertThat(e.code()).isEqualTo(ApiErrorCode.FEED_BOARD_INVALID);
                    assertThat(e.getMessage()).startsWith("A board feed takes");
                });
        verify(feeds, never()).save(any(IngestionFeed.class));
    }

    @Test
    void a_board_run_tells_the_engine_which_company_its_rows_belong_to() {
        IngestionFeed feed = feed("Acme", "https://api.lever.co/v0/postings/acme?mode=json", "lever");
        when(feeds.findByIdAndUserId(feedId, userId)).thenReturn(Optional.of(feed));
        when(fetcher.fetch(feed.getUrl())).thenReturn("[]");
        when(jobs.findByStatusOrderByPostedAtDescIdDesc(eq("open"), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of()));
        when(ai.planIngest(any(), any(), anyList(), anyInt(), anyInt(), any(), any()))
                .thenReturn(Map.of("counts", Map.of()));

        service.runNow(userId, feedId);

        verify(ai).planIngest(eq("[]"), eq("lever"), anyList(), eq(60), eq(30),
                eq(userId), eq("Acme"));
    }

    @Test
    void the_twenty_first_feed_is_refused() {
        when(feeds.countByUserId(userId)).thenReturn(20L);

        assertThatThrownBy(() -> service.createFeed(userId,
                new FeedRequest("One more", "https://boards.example.com/rss", null)))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.code()).isEqualTo(ApiErrorCode.FEED_LIMIT_REACHED));
    }

    @Test
    void switching_a_feed_off_keeps_its_last_run_visible() {
        IngestionFeed feed = feed();
        IngestionRun last = new IngestionRun();
        last.setFeedId(feedId);
        last.setStatus(IngestionRun.STATUS_COMPLETED);
        last.setStartedAt(OffsetDateTime.now().minusHours(4));
        when(feeds.findByIdAndUserId(feedId, userId)).thenReturn(Optional.of(feed));
        when(feeds.save(any(IngestionFeed.class))).thenAnswer(i -> i.getArgument(0));
        when(runs.findFirstByFeedIdOrderByStartedAtDesc(feedId)).thenReturn(Optional.of(last));

        FeedItem item = service.setEnabled(userId, feedId, false);

        assertThat(item.enabled()).isFalse();
        assertThat(item.lastRun()).isNotNull();
        assertThat(item.lastRun().status()).isEqualTo(IngestionRun.STATUS_COMPLETED);
    }

    @Test
    void deleting_another_users_feed_is_a_404() {
        when(feeds.findByIdAndUserId(feedId, userId)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.deleteFeed(userId, feedId))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.code()).isEqualTo(ApiErrorCode.INGESTION_FEED_NOT_FOUND));
        verify(feeds, never()).delete(any(IngestionFeed.class));
    }

    @Test
    void the_run_list_is_a_page_clamped_like_every_other_board() {
        when(feeds.findByUserIdOrderByCreatedAtDesc(userId)).thenReturn(List.of());
        when(runs.findByUserIdOrderByStartedAtDescIdDesc(eq(userId), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of()));

        service.listRuns(userId, -3, 0);
        service.listRuns(userId, 2, 999);

        ArgumentCaptor<Pageable> cap = ArgumentCaptor.forClass(Pageable.class);
        verify(runs, times(2)).findByUserIdOrderByStartedAtDescIdDesc(eq(userId), cap.capture());
        assertThat(cap.getAllValues().get(0).getPageNumber()).isZero();
        assertThat(cap.getAllValues().get(0).getPageSize()).isEqualTo(1);
        assertThat(cap.getAllValues().get(1).getPageNumber()).isEqualTo(2);
        assertThat(cap.getAllValues().get(1).getPageSize()).isEqualTo(100);
    }

    @Test
    void a_run_list_names_the_feed_it_came_from() {
        IngestionFeed feed = feed();
        IngestionRun run = new IngestionRun();
        run.setFeedId(feedId);
        run.setStatus(IngestionRun.STATUS_COMPLETED);
        run.setStartedAt(OffsetDateTime.now());
        when(feeds.findByUserIdOrderByCreatedAtDesc(userId)).thenReturn(List.of(feed));
        when(runs.findByUserIdOrderByStartedAtDescIdDesc(eq(userId), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(run)));

        assertThat(service.listRuns(userId, 0, 20).items().get(0).feedName())
                .isEqualTo("Hiring board");
    }

    @Test
    void another_users_run_is_a_404_named_for_runs() {
        UUID runId = UUID.randomUUID();
        when(runs.findByIdAndUserId(runId, userId)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.runDetail(userId, runId))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.code()).isEqualTo(ApiErrorCode.INGESTION_RUN_NOT_FOUND));
    }

    @Test
    void the_detailed_run_carries_the_stored_plan() {
        UUID runId = UUID.randomUUID();
        IngestionFeed feed = feed();
        IngestionRun run = new IngestionRun();
        run.setUserId(userId);
        run.setFeedId(feedId);
        run.setStatus(IngestionRun.STATUS_COMPLETED);
        run.setStartedAt(OffsetDateTime.now());
        run.setPlan(Map.of("counts", Map.of("incoming", 1)));
        when(runs.findByIdAndUserId(runId, userId)).thenReturn(Optional.of(run));
        when(feeds.findById(feedId)).thenReturn(Optional.of(feed));

        RunDetail detail = service.runDetail(userId, runId);

        assertThat(detail.run().feedName()).isEqualTo("Hiring board");
        assertThat(detail.plan()).containsKey("counts");
    }

    @Test
    void the_sweep_visits_every_enabled_feed_even_when_one_filing_fails() {
        IngestionFeed first = feed();
        IngestionFeed second = feed("Second board", "https://second.example.com/rss", "feed");
        ReflectionTestUtils.setField(second, "id", UUID.randomUUID());
        when(feeds.findByEnabledTrueOrderByCreatedAtAsc()).thenReturn(List.of(first, second));
        when(fetcher.fetch(any())).thenReturn("<rss/>");
        when(jobs.findByStatusOrderByPostedAtDescIdDesc(eq("open"), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of()));
        when(ai.planIngest(any(), any(), anyList(), anyInt(), anyInt(), any(), any()))
                .thenReturn(Map.of("counts", Map.of()));
        when(runs.save(any(IngestionRun.class)))
                .thenThrow(new IllegalStateException("db down"))
                .thenAnswer(i -> i.getArgument(0));

        int due = service.sweepEnabled();

        assertThat(due).isEqualTo(2);
        verify(runs, times(2)).save(any(IngestionRun.class));
        verify(fetcher, times(2)).fetch(any());
    }

    @Test
    void the_sweep_answers_zero_on_a_night_with_nothing_due() {
        when(feeds.findByEnabledTrueOrderByCreatedAtAsc()).thenReturn(List.of());

        assertThat(service.sweepEnabled()).isZero();
        verify(fetcher, never()).fetch(any());
    }

    @Test
    void a_completed_pull_counts_itself_and_moves_the_success_marker() {
        IngestionFeed feed = feed();
        when(feeds.findByIdAndUserId(feedId, userId)).thenReturn(Optional.of(feed));
        when(fetcher.fetch(feed.getUrl())).thenReturn("<rss/>");
        when(jobs.findByStatusOrderByPostedAtDescIdDesc(eq("open"), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of()));
        when(ai.planIngest(any(), any(), anyList(), anyInt(), anyInt(), any(), any()))
                .thenReturn(Map.of("counts", Map.of()));

        RunDetail detail = service.runNow(userId, feedId);

        assertThat(detail.run().status()).isEqualTo(IngestionRun.STATUS_COMPLETED);
        assertThat(counter(IngestionRun.STATUS_COMPLETED)).isEqualTo(1.0);
        assertThat(counter(IngestionRun.STATUS_FAILED)).isZero();
        assertThat(successMarker()).isEqualTo(detail.run().finishedAt().toEpochSecond());
    }

    @Test
    void a_failed_pull_counts_itself_and_leaves_the_success_marker_alone() {
        IngestionFeed feed = feed();
        when(feeds.findByIdAndUserId(feedId, userId)).thenReturn(Optional.of(feed));
        when(fetcher.fetch(feed.getUrl()))
                .thenThrow(new IllegalStateException("Feed answered HTTP 503"));
        double before = successMarker();

        RunDetail detail = service.runNow(userId, feedId);

        assertThat(detail.run().status()).isEqualTo(IngestionRun.STATUS_FAILED);
        assertThat(counter(IngestionRun.STATUS_FAILED)).isEqualTo(1.0);
        assertThat(counter(IngestionRun.STATUS_COMPLETED)).isZero();
        assertThat(successMarker())
                .as("a failed pull must not read as a success, or the alarm above it cannot fire")
                .isEqualTo(before);
    }

    @Test
    void applying_a_plan_creates_the_company_and_the_job_it_names() {
        IngestionFeed feed = feed();
        Map<String, Object> plan = plan(
                List.of(row("title", "Backend Engineer", "company", "Acme",
                        "location", "Hangzhou", "remote_type", "remote",
                        "employment_type", "full_time", "salary_min", 30000,
                        "salary_max", 45000, "salary_currency", "CNY",
                        "description", "Build things", "skills", List.of("Java", "SQL"),
                        "external_url", "https://acme.example/jobs/1")),
                List.of(), List.of());
        IngestionRun run = runWithPlan(plan);
        when(runs.findWithLockByIdAndUserId(run.getId(), userId)).thenReturn(Optional.of(run));
        when(feeds.findById(feedId)).thenReturn(Optional.of(feed));
        when(companies.findByName("Acme")).thenReturn(Optional.empty());
        when(companies.save(any(Company.class))).thenAnswer(i -> {
            Company company = i.getArgument(0);
            ReflectionTestUtils.setField(company, "id", companyId);
            return company;
        });
        when(jobs.save(any(Job.class))).thenAnswer(i -> i.getArgument(0));

        ApplyResult result = service.applyRun(userId, run.getId());

        assertThat(result.created()).isEqualTo(1);
        assertThat(result.updated()).isZero();
        assertThat(result.closed()).isZero();
        ArgumentCaptor<Job> saved = ArgumentCaptor.forClass(Job.class);
        verify(jobs).save(saved.capture());
        Job job = saved.getValue();
        assertThat(job.getCompanyId()).isEqualTo(companyId);
        assertThat(job.getTitle()).isEqualTo("Backend Engineer");
        assertThat(job.getLocation()).isEqualTo("Hangzhou");
        assertThat(job.getRemoteType()).isEqualTo("remote");
        assertThat(job.getSalaryMin()).isEqualTo(30000);
        assertThat(job.getSkills()).containsExactly("Java", "SQL");
        assertThat(job.getExternalUrl()).isEqualTo("https://acme.example/jobs/1");
        assertThat(job.getStatus()).isEqualTo("open");
        assertThat(job.getSource()).isEqualTo("rss");
        assertThat(run.getAppliedAt()).isNotNull();
        assertThat(run.getAppliedCounts()).containsEntry("created", 1);
    }

    @Test
    void a_known_company_is_reused_and_a_nameless_row_belongs_to_the_feed() {
        IngestionFeed feed = feed();
        Map<String, Object> plan = plan(
                List.of(row("title", "Backend Engineer", "company", "Acme"),
                        row("title", "Unnamed posting")),
                List.of(), List.of());
        IngestionRun run = runWithPlan(plan);
        when(runs.findWithLockByIdAndUserId(run.getId(), userId)).thenReturn(Optional.of(run));
        when(feeds.findById(feedId)).thenReturn(Optional.of(feed));
        when(companies.findByName("Acme")).thenReturn(Optional.of(company()));
        when(companies.findByName("Hiring board")).thenReturn(Optional.empty());
        when(companies.save(any(Company.class))).thenAnswer(i -> {
            Company created = i.getArgument(0);
            ReflectionTestUtils.setField(created, "id", UUID.randomUUID());
            return created;
        });
        when(jobs.save(any(Job.class))).thenAnswer(i -> i.getArgument(0));

        ApplyResult result = service.applyRun(userId, run.getId());

        assertThat(result.created()).isEqualTo(2);
        verify(companies, never()).save(argThat(c -> "Acme".equals(c.getName())));
        verify(companies).save(argThat(c -> "Hiring board".equals(c.getName())));
        assertThat(savedJobs()).extracting(Job::getCompanyId)
                .containsExactly(companyId, savedCompanyId());
    }

    @Test
    void an_update_refreshes_the_row_the_engine_matched_and_reopens_it() {
        IngestionFeed feed = feed();
        Job existing = openJob();
        existing.setStatus("closed");
        Map<String, Object> plan = plan(List.of(),
                List.of(row("existingId", jobId.toString(), "title", "Backend Engineer II",
                        "location", "Shanghai", "remote_type", "hybrid",
                        "employment_type", "full_time", "salary_min", 32000,
                        "salary_max", 48000, "salary_currency", "CNY",
                        "description", "Build more", "skills", List.of("Kotlin"),
                        "external_url", "https://acme.example/jobs/1")),
                List.of());
        IngestionRun run = runWithPlan(plan);
        when(runs.findWithLockByIdAndUserId(run.getId(), userId)).thenReturn(Optional.of(run));
        when(feeds.findById(feedId)).thenReturn(Optional.of(feed));
        when(jobs.findById(jobId)).thenReturn(Optional.of(existing));
        when(jobs.save(any(Job.class))).thenAnswer(i -> i.getArgument(0));

        ApplyResult result = service.applyRun(userId, run.getId());

        assertThat(result.created()).isZero();
        assertThat(result.updated()).isEqualTo(1);
        assertThat(existing.getTitle()).isEqualTo("Backend Engineer II");
        assertThat(existing.getLocation()).isEqualTo("Shanghai");
        assertThat(existing.getStatus()).isEqualTo("open");
        assertThat(existing.getSkills()).containsExactly("Kotlin");
        assertThat(existing.getSalaryMax()).isEqualTo(48000);
    }

    @Test
    void an_update_whose_row_vanished_is_created_from_tonights_reading() {
        IngestionFeed feed = feed();
        Map<String, Object> plan = plan(List.of(),
                List.of(row("existingId", jobId.toString(), "title", "Backend Engineer",
                        "company", "Acme")),
                List.of());
        IngestionRun run = runWithPlan(plan);
        when(runs.findWithLockByIdAndUserId(run.getId(), userId)).thenReturn(Optional.of(run));
        when(feeds.findById(feedId)).thenReturn(Optional.of(feed));
        when(jobs.findById(jobId)).thenReturn(Optional.empty());
        when(companies.findByName("Acme")).thenReturn(Optional.of(company()));
        when(jobs.save(any(Job.class))).thenAnswer(i -> i.getArgument(0));

        ApplyResult result = service.applyRun(userId, run.getId());

        assertThat(result.created()).isEqualTo(1);
        assertThat(result.updated()).isZero();
        assertThat(savedJob().getCompanyId()).isEqualTo(companyId);
    }

    @Test
    void a_close_row_closes_the_job_it_names_once() {
        IngestionFeed feed = feed();
        Job existing = openJob();
        IngestionRun first = runWithPlan(plan(List.of(), List.of(),
                List.of(Map.of("id", jobId.toString(), "title", "Backend Engineer"))));
        when(runs.findWithLockByIdAndUserId(first.getId(), userId)).thenReturn(Optional.of(first));
        when(feeds.findById(feedId)).thenReturn(Optional.of(feed));
        when(jobs.findById(jobId)).thenReturn(Optional.of(existing));
        when(jobs.save(any(Job.class))).thenAnswer(i -> i.getArgument(0));

        ApplyResult result = service.applyRun(userId, first.getId());

        assertThat(result.closed()).isEqualTo(1);
        assertThat(existing.getStatus()).isEqualTo("closed");
    }

    @Test
    void a_second_apply_is_refused_rather_than_writing_the_plan_twice() {
        IngestionRun run = runWithPlan(plan(List.of(row("title", "Backend Engineer")),
                List.of(), List.of()));
        run.setAppliedAt(OffsetDateTime.now());
        when(runs.findWithLockByIdAndUserId(run.getId(), userId)).thenReturn(Optional.of(run));

        assertThatThrownBy(() -> service.applyRun(userId, run.getId()))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.code())
                                .isEqualTo(ApiErrorCode.INGESTION_RUN_ALREADY_APPLIED));
        verify(jobs, never()).save(any(Job.class));
    }

    @Test
    void a_failed_run_has_no_plan_to_apply() {
        IngestionRun run = runWithPlan(null);
        run.setStatus(IngestionRun.STATUS_FAILED);
        when(runs.findWithLockByIdAndUserId(run.getId(), userId)).thenReturn(Optional.of(run));

        assertThatThrownBy(() -> service.applyRun(userId, run.getId()))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.code())
                                .isEqualTo(ApiErrorCode.INGESTION_RUN_NOT_APPLICABLE));
    }

    @Test
    void another_users_run_is_not_the_callers_to_apply() {
        UUID runId = UUID.randomUUID();
        when(runs.findWithLockByIdAndUserId(runId, userId)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.applyRun(userId, runId))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.code()).isEqualTo(ApiErrorCode.INGESTION_RUN_NOT_FOUND));
    }

    @Test
    void a_create_row_with_no_title_is_not_a_posting() {
        IngestionFeed feed = feed();
        IngestionRun run = runWithPlan(plan(List.of(row("title", "  ", "company", "Acme")),
                List.of(), List.of()));
        when(runs.findWithLockByIdAndUserId(run.getId(), userId)).thenReturn(Optional.of(run));
        when(feeds.findById(feedId)).thenReturn(Optional.of(feed));

        ApplyResult result = service.applyRun(userId, run.getId());

        assertThat(result.created()).isZero();
        verify(jobs, never()).save(any(Job.class));
        verify(companies, never()).save(any(Company.class));
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> plan(List<Map<String, Object>> create,
                                            List<Map<String, Object>> update,
                                            List<Map<String, Object>> close) {
        Map<String, Object> plan = new LinkedHashMap<>();
        plan.put("create", create);
        plan.put("update", update);
        plan.put("close", close);
        return plan;
    }

    private static Map<String, Object> row(Object... pairs) {
        Map<String, Object> row = new LinkedHashMap<>();
        for (int i = 0; i < pairs.length; i += 2) {
            row.put(String.valueOf(pairs[i]), pairs[i + 1]);
        }
        return row;
    }

    private IngestionRun runWithPlan(Map<String, Object> plan) {
        IngestionRun run = new IngestionRun();
        ReflectionTestUtils.setField(run, "id", UUID.randomUUID());
        run.setUserId(userId);
        run.setFeedId(feedId);
        run.setStatus(IngestionRun.STATUS_COMPLETED);
        run.setStartedAt(OffsetDateTime.now());
        run.setFinishedAt(OffsetDateTime.now());
        run.setPlan(plan);
        return run;
    }

    @SuppressWarnings("unchecked")
    private List<Job> savedJobs() {
        ArgumentCaptor<Job> saved = ArgumentCaptor.forClass(Job.class);
        verify(jobs, times(2)).save(saved.capture());
        return saved.getAllValues();
    }

    private Job savedJob() {
        ArgumentCaptor<Job> saved = ArgumentCaptor.forClass(Job.class);
        verify(jobs).save(saved.capture());
        return saved.getValue();
    }

    private UUID savedCompanyId() {
        ArgumentCaptor<Company> saved = ArgumentCaptor.forClass(Company.class);
        verify(companies).save(saved.capture());
        return (UUID) ReflectionTestUtils.getField(saved.getValue(), "id");
    }

    private double counter(String status) {
        return registry.get(IngestionMetrics.RUNS).tag("status", status).counter().count();
    }

    private double successMarker() {
        return registry.get(IngestionMetrics.LAST_SUCCESS).gauge().value();
    }
}
