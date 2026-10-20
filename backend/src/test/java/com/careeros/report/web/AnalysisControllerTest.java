package com.careeros.report.web;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.careeros.application.entity.Application;
import com.careeros.application.repository.ApplicationRepository;
import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUserArgumentResolver;
import com.careeros.common.EnvelopeAdvice;
import com.careeros.common.GlobalExceptionHandler;
import com.careeros.report.service.AnalysisService;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.Pageable;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

/**
 * The analytics routes (Epics 15.1-15.3).
 *
 * <p>All three read the caller's own application rows, so the service hands the
 * engine a list of row-shaped maps. What this pins is that the rows carry the
 * engine's own field names — a row with a snake_case key the engine does not
 * read is a row the engine sees as a title and nothing else — and that the
 * caller's id travels with them.
 */
class AnalysisControllerTest {

    private static final String USER = "6b0178a0-d352-09c3-ea65-8f107bd28d01";

    private com.careeros.ai.AiServiceClient ai;
    private ApplicationRepository applications;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        ai = mock(com.careeros.ai.AiServiceClient.class);
        applications = mock(ApplicationRepository.class);
        AnalysisService service = new AnalysisService(ai, applications);
        AnalysisController controller = new AnalysisController(service);
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

    private Application application() {
        Application a = new Application();
        // The id and the timestamps are written by the database, so the test
        // fills them the way the persistence layer would: through the fields the
        // entity exposes.
        a.setTitle("Backend Engineer");
        a.setCompanyName("FakeCorp");
        a.setStatus("applied");
        a.setAppliedAt(OffsetDateTime.parse("2026-09-01T00:00:00+00:00"));
        return a;
    }

    @Test
    void the_digest_is_the_engines_answer_wrapped_once() throws Exception {
        when(applications.findByUserIdOrderByUpdatedAtDescIdAsc(eq(UUID.fromString(USER)), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(application())));
        when(ai.insightDigest(eq(UUID.fromString(USER)), any()))
                .thenReturn(Map.of("totalApplications", 1, "stalledCount", 0));

        mvc.perform(get("/api/v1/analysis/insight-digest"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.totalApplications").value(1));

        @SuppressWarnings("unchecked")
        ArgumentCaptor<List<Map<String, Object>>> rows = ArgumentCaptor.forClass(List.class);
        verify(ai).insightDigest(eq(UUID.fromString(USER)), rows.capture());
        Map<String, Object> row = rows.getValue().get(0);
        // The engine's own field names: it reads `applied_at` and `created_at`,
        // not the Java column names. A field the row does not carry is left out
        // rather than sent as null -- so `created_at` is absent here, because
        // this row's timestamps are written by the database.
        assertThat(row).containsEntry("status", "applied");
        assertThat(row).containsEntry("company", "FakeCorp");
        assertThat(row).containsEntry("title", "Backend Engineer");
        assertThat(row).containsKey("applied_at");
        assertThat(row).containsKey("id");
        assertThat(row).doesNotContainKey("created_at");
    }

    @Test
    void the_funnel_reads_the_same_rows() throws Exception {
        when(applications.findByUserIdOrderByUpdatedAtDescIdAsc(eq(UUID.fromString(USER)), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(application())));
        when(ai.pipelineFunnel(eq(UUID.fromString(USER)), any()))
                .thenReturn(Map.of("appliedCount", 1, "pipeline", List.of()));

        mvc.perform(get("/api/v1/analysis/pipeline-funnel"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.appliedCount").value(1));

        verify(ai).pipelineFunnel(eq(UUID.fromString(USER)), any());
    }

    @Test
    void the_rates_read_the_same_rows() throws Exception {
        when(applications.findByUserIdOrderByUpdatedAtDescIdAsc(eq(UUID.fromString(USER)), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(application())));
        when(ai.responseRate(eq(UUID.fromString(USER)), any()))
                .thenReturn(Map.of("appliedCount", 1, "responseRate", 0.5));

        mvc.perform(get("/api/v1/analysis/response-rate"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.responseRate").value(0.5));

        verify(ai).responseRate(eq(UUID.fromString(USER)), any());
    }

    /**
     * An account with no applications is a real state, not an error: the
     * engine answers "the funnel is empty", which is the honest digest for a
     * workspace that has not started.
     */
    @Test
    void an_account_with_no_applications_answers_empty_rather_than_failing() throws Exception {
        when(applications.findByUserIdOrderByUpdatedAtDescIdAsc(eq(UUID.fromString(USER)), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of()));
        when(ai.insightDigest(eq(UUID.fromString(USER)), any()))
                .thenReturn(Map.of("totalApplications", 0));

        mvc.perform(get("/api/v1/analysis/insight-digest"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.totalApplications").value(0));
    }
}
