package com.careeros.job.web;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.isNull;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.careeros.ai.AiServiceClient;
import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUserArgumentResolver;
import com.careeros.common.EnvelopeAdvice;
import com.careeros.common.GlobalExceptionHandler;
import com.careeros.job.service.JobIngestionService;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.http.MediaType;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

/**
 * The job-ingestion routes (Epics 14.2-14.3).
 *
 * <p>Two things are worth pinning. The first is the windows: the engine has its
 * own defaults, and a caller who names no window must get the engine's, not
 * the bridge's guess. The second is the user context — the ingestion runs under
 * the caller's id, because a sweep that wrote rows under a random id would put
 * another user's jobs in this one's board.
 */
class JobIngestionControllerTest {

    private static final String USER = "6b0178a0-d352-09c3-ea65-8f107bd28d01";

    private AiServiceClient ai;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        ai = mock(AiServiceClient.class);
        JobIngestionService service = new JobIngestionService(ai);
        JobIngestionController controller = new JobIngestionController(service);
        mvc = MockMvcBuilders.standaloneSetup(controller)
                .setControllerAdvice(new EnvelopeAdvice(), new GlobalExceptionHandler())
                .setCustomArgumentResolvers(new CurrentUserArgumentResolver())
                .build();
        SecurityContextHolder.getContext().setAuthentication(new UsernamePasswordAuthenticationToken(
                new AuthUser(UUID.fromString(USER), "ada@example.invalid", "user"), null, List.of()));
    }

    @AfterEach
    void tearDown() {
        SecurityContextHolder.clearContext();
    }

    @Test
    void the_parse_carries_the_feed_under_the_callers_context() throws Exception {
        when(ai.parseFeed(anyString(), anyString(), any()))
                .thenReturn(Map.of("postings", List.of(Map.of("title", "Backend Engineer")), "count", 1));

        mvc.perform(post("/api/v1/jobs/ingest/parse")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"feed\":\"<rss></rss>\",\"source\":\"rss\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.count").value(1));

        verify(ai).parseFeed(eq("<rss></rss>"), eq("rss"), eq(UUID.fromString(USER)));
    }

    /**
     * The engine owns its defaults: a caller who names no window gets the
     * engine's, so the bridge passes the engine's own numbers rather than
     * making up its own.
     */
    @Test
    void a_sweep_with_no_windows_uses_the_engines_own_defaults() throws Exception {
        when(ai.freshnessSweep(any(), anyInt(), anyInt(), any()))
                .thenReturn(Map.of("counts", Map.of("fresh", 1, "stale", 0, "expired", 0, "undated", 0)));

        mvc.perform(post("/api/v1/jobs/ingest/freshness-sweep")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"postings\":[{\"title\":\"Backend Engineer\"}]}"))
                .andExpect(status().isOk());

        verify(ai).freshnessSweep(any(), eq(60), eq(30), eq(UUID.fromString(USER)));
    }

    @Test
    void a_sweep_with_named_windows_passes_them_through() throws Exception {
        when(ai.freshnessSweep(any(), anyInt(), anyInt(), any()))
                .thenReturn(Map.of("counts", Map.of("fresh", 0, "stale", 1, "expired", 0, "undated", 0)));

        mvc.perform(post("/api/v1/jobs/ingest/freshness-sweep")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"postings":[{"title":"Backend Engineer"}],
                                 "maxAgeDays":30,"staleSeenDays":10}
                                """))
                .andExpect(status().isOk());

        verify(ai).freshnessSweep(any(), eq(30), eq(10), eq(UUID.fromString(USER)));
    }

    @Test
    void the_plan_carries_the_feed_and_the_existing_corpus() throws Exception {
        when(ai.planIngest(anyString(), anyString(), any(), anyInt(), anyInt(), any(), any()))
                .thenReturn(Map.of("counts", Map.of("incoming", 1, "create", 1, "update", 0,
                        "close", 0, "duplicates", 0)));

        mvc.perform(post("/api/v1/jobs/ingest/plan")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"feed":"<rss></rss>","source":"rss",
                                 "existing":[{"id":"11111111-1111-1111-1111-111111111111"}]}
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.counts.create").value(1));

        @SuppressWarnings("unchecked")
        ArgumentCaptor<List<Map<String, Object>>> existing = ArgumentCaptor.forClass(List.class);
        verify(ai).planIngest(eq("<rss></rss>"), eq("rss"), existing.capture(),
                eq(60), eq(30), eq(UUID.fromString(USER)), isNull());
        assertThat(existing.getValue()).hasSize(1);
    }

    /**
     * A feed with no source names the default connector rather than none: a
     * plan built under the wrong source would label every row wrongly.
     */
    @Test
    void a_plan_with_no_source_names_the_default_connector() throws Exception {
        when(ai.planIngest(anyString(), anyString(), any(), anyInt(), anyInt(), any(), any()))
                .thenReturn(Map.of("counts", Map.of("incoming", 0, "create", 0, "update", 0,
                        "close", 0, "duplicates", 0)));

        mvc.perform(post("/api/v1/jobs/ingest/plan")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"feed\":\"<rss></rss>\"}"))
                .andExpect(status().isOk());

        verify(ai).planIngest(eq("<rss></rss>"), eq("rss"), any(), eq(60), eq(30),
                eq(UUID.fromString(USER)), isNull());
    }
}
