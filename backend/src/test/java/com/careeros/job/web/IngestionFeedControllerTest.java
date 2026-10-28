package com.careeros.job.web;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUserArgumentResolver;
import com.careeros.common.EnvelopeAdvice;
import com.careeros.common.GlobalExceptionHandler;
import com.careeros.common.PageDTO;
import com.careeros.job.dto.IngestionFeedDtos.ApplyResult;
import com.careeros.job.dto.IngestionFeedDtos.FeedItem;
import com.careeros.job.dto.IngestionFeedDtos.FeedRequest;
import com.careeros.job.dto.IngestionFeedDtos.RunDetail;
import com.careeros.job.dto.IngestionFeedDtos.RunItem;
import com.careeros.job.entity.IngestionRun;
import com.careeros.job.service.ScheduledIngestionService;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

/**
 * The ingestion routes (roadmap 19.2).
 *
 * <p>Two things are worth a route-level test. The first is ownership: every handler is
 * handed the caller's id, so a sweep only ever fetches a user's own subscriptions. The
 * second is that a failed pull is not an HTTP failure — the run list has to be able to
 * show "the feed answered 503" as a 200 with a status, or the reader sees an error page
 * instead of the explanation the sweep already wrote down.
 */
class IngestionFeedControllerTest {

    private static final UUID ALICE = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final UUID FEED = UUID.fromString("33333333-3333-4333-8333-333333333333");
    private static final UUID RUN = UUID.fromString("44444444-4444-4444-8444-444444444444");

    private ScheduledIngestionService ingestion;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        ingestion = mock(ScheduledIngestionService.class);
        mvc = MockMvcBuilders.standaloneSetup(new IngestionFeedController(ingestion))
                .setControllerAdvice(new EnvelopeAdvice(), new GlobalExceptionHandler())
                .setCustomArgumentResolvers(new CurrentUserArgumentResolver())
                .build();
        SecurityContextHolder.getContext().setAuthentication(new UsernamePasswordAuthenticationToken(
                new AuthUser(ALICE, "ada@example.invalid", "user"), null, List.of()));
    }

    @AfterEach
    void tearDown() {
        SecurityContextHolder.clearContext();
    }

    private static RunItem run(String status, String error) {
        return new RunItem(RUN, FEED, "Hiring board", status, error,
                Map.of("incoming", 4, "create", 2), OffsetDateTime.now().minusMinutes(1),
                OffsetDateTime.now(), null, null);
    }

    private static FeedItem feed(boolean enabled) {
        return new FeedItem(FEED, "Hiring board", "https://boards.example.com/rss", "rss",
                enabled, OffsetDateTime.now(), run("completed", null));
    }

    @Test
    void the_feed_list_is_the_callers_own() throws Exception {
        when(ingestion.listFeeds(ALICE)).thenReturn(List.of(feed(true)));

        mvc.perform(get("/api/v1/ingestion/feeds"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data[0].name").value("Hiring board"))
                .andExpect(jsonPath("$.data[0].lastRun.status").value("completed"));

        verify(ingestion).listFeeds(ALICE);
    }

    @Test
    void a_feed_is_created_201_with_its_three_fields() throws Exception {
        when(ingestion.createFeed(eq(ALICE), any(FeedRequest.class))).thenReturn(feed(true));

        mvc.perform(post("/api/v1/ingestion/feeds")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"name":"Hiring board",
                                 "url":"https://boards.example.com/rss",
                                 "source":"rss"}
                                """))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.data.source").value("rss"));

        verify(ingestion).createFeed(ALICE,
                new FeedRequest("Hiring board", "https://boards.example.com/rss", "rss"));
    }

    @Test
    void a_blank_name_or_url_is_refused_before_the_service_sees_it() throws Exception {
        mvc.perform(post("/api/v1/ingestion/feeds")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"name\":\" \",\"url\":\"https://boards.example.com/rss\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("VALIDATION_FAILED"));

        mvc.perform(post("/api/v1/ingestion/feeds")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"name\":\"Board\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("VALIDATION_FAILED"));
    }

    @Test
    void the_enabled_switch_is_the_only_patch_a_feed_takes() throws Exception {
        when(ingestion.setEnabled(ALICE, FEED, false)).thenReturn(feed(false));

        mvc.perform(patch("/api/v1/ingestion/feeds/{id}", FEED)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"enabled\":false}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.enabled").value(false));

        mvc.perform(patch("/api/v1/ingestion/feeds/{id}", FEED)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("VALIDATION_FAILED"));
    }

    @Test
    void deleting_a_feed_is_a_204() throws Exception {
        mvc.perform(delete("/api/v1/ingestion/feeds/{id}", FEED))
                .andExpect(status().isNoContent());

        verify(ingestion).deleteFeed(ALICE, FEED);
    }

    @Test
    void a_dead_feed_answers_200_with_a_failed_run_rather_than_a_server_error() throws Exception {
        when(ingestion.runNow(ALICE, FEED)).thenReturn(new RunDetail(
                run(IngestionRun.STATUS_FAILED, "Feed answered HTTP 503"), null));

        mvc.perform(post("/api/v1/ingestion/feeds/{id}/run", FEED))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.run.status").value("failed"))
                .andExpect(jsonPath("$.data.run.error").value("Feed answered HTTP 503"));
    }

    @Test
    void the_run_list_is_a_page_whose_window_defaults_to_twenty() throws Exception {
        when(ingestion.listRuns(ALICE, 1, 5))
                .thenReturn(PageDTO.of(List.of(run("completed", null)), 6, 1, 5));
        when(ingestion.listRuns(ALICE, 0, 20)).thenReturn(PageDTO.of(List.of(), 0, 0, 20));

        mvc.perform(get("/api/v1/ingestion/runs").param("page", "1").param("size", "5"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.items[0].counts.create").value(2))
                .andExpect(jsonPath("$.data.total").value(6))
                .andExpect(jsonPath("$.data.page").value(1))
                .andExpect(jsonPath("$.data.size").value(5));
        mvc.perform(get("/api/v1/ingestion/runs"))
                .andExpect(status().isOk());

        verify(ingestion).listRuns(ALICE, 1, 5);
        verify(ingestion).listRuns(ALICE, 0, 20);
    }

    @Test
    void one_run_carries_the_stored_plan() throws Exception {
        when(ingestion.runDetail(ALICE, RUN)).thenReturn(new RunDetail(
                run(IngestionRun.STATUS_COMPLETED, null), Map.of("counts", Map.of("create", 2))));

        mvc.perform(get("/api/v1/ingestion/runs/{id}", RUN))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.run.status").value("completed"))
                .andExpect(jsonPath("$.data.plan.counts.create").value(2));
    }

    @Test
    void another_users_run_is_a_404_naming_the_code() throws Exception {
        when(ingestion.runDetail(ALICE, RUN)).thenThrow(
                new ApiException(ApiErrorCode.INGESTION_RUN_NOT_FOUND, "Ingestion run not found"));

        mvc.perform(get("/api/v1/ingestion/runs/{id}", RUN))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error.code").value("INGESTION_RUN_NOT_FOUND"));
    }

    @Test
    void another_users_feed_is_a_404_naming_the_code() throws Exception {
        doThrow(new ApiException(ApiErrorCode.INGESTION_FEED_NOT_FOUND, "Feed not found"))
                .when(ingestion).deleteFeed(ALICE, FEED);

        mvc.perform(delete("/api/v1/ingestion/feeds/{id}", FEED))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error.code").value("INGESTION_FEED_NOT_FOUND"));
    }

    @Test
    void every_route_is_scoped_to_the_caller() throws Exception {
        when(ingestion.listFeeds(ALICE)).thenReturn(List.of());
        when(ingestion.listRuns(ALICE, 0, 20)).thenReturn(PageDTO.of(List.of(), 0, 0, 20));

        mvc.perform(get("/api/v1/ingestion/feeds")).andExpect(status().isOk());
        mvc.perform(get("/api/v1/ingestion/runs")).andExpect(status().isOk());

        verify(ingestion).listFeeds(ALICE);
        verify(ingestion).listRuns(ALICE, 0, 20);
    }

    @Test
    void apply_writes_the_plan_and_answers_with_the_three_counts() throws Exception {
        OffsetDateTime at = OffsetDateTime.now();
        when(ingestion.applyRun(ALICE, RUN)).thenReturn(new ApplyResult(2, 1, 3, at));

        mvc.perform(post("/api/v1/ingestion/runs/{id}/apply", RUN))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.created").value(2))
                .andExpect(jsonPath("$.data.updated").value(1))
                .andExpect(jsonPath("$.data.closed").value(3))
                .andExpect(jsonPath("$.data.appliedAt").exists());

        verify(ingestion).applyRun(ALICE, RUN);
    }

    @Test
    void applying_twice_is_a_409_naming_the_code() throws Exception {
        when(ingestion.applyRun(ALICE, RUN)).thenThrow(
                new ApiException(ApiErrorCode.INGESTION_RUN_ALREADY_APPLIED, "Already applied"));

        mvc.perform(post("/api/v1/ingestion/runs/{id}/apply", RUN))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.error.code").value("INGESTION_RUN_ALREADY_APPLIED"));
    }

    @Test
    void a_failed_run_is_not_applicable_and_the_route_says_so() throws Exception {
        when(ingestion.applyRun(ALICE, RUN)).thenThrow(
                new ApiException(ApiErrorCode.INGESTION_RUN_NOT_APPLICABLE, "Run has no plan"));

        mvc.perform(post("/api/v1/ingestion/runs/{id}/apply", RUN))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.error.code").value("INGESTION_RUN_NOT_APPLICABLE"));
    }

    @Test
    void another_users_run_cannot_be_applied() throws Exception {
        when(ingestion.applyRun(ALICE, RUN)).thenThrow(
                new ApiException(ApiErrorCode.INGESTION_RUN_NOT_FOUND, "Ingestion run not found"));

        mvc.perform(post("/api/v1/ingestion/runs/{id}/apply", RUN))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error.code").value("INGESTION_RUN_NOT_FOUND"));
    }
}
