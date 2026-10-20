package com.careeros.report.web;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.isNull;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.careeros.ai.AiServiceClient;
import com.careeros.ai.repository.GrowthPlanRepository;
import com.careeros.application.repository.ApplicationRepository;
import com.careeros.report.service.ExportService;
import com.careeros.report.service.ImportService;
import com.careeros.auth.repository.UserProfileRepository;
import com.careeros.knowledge.repository.UserNoteRepository;
import com.careeros.knowledge.service.KnowledgeService;
import com.careeros.interview.repository.InterviewEvaluationRepository;
import com.careeros.interview.repository.InterviewSessionRepository;
import com.careeros.interview.repository.InterviewTurnRepository;
import com.careeros.job.repository.JobJdRepository;
import com.careeros.job.repository.JobRepository;
import com.careeros.resume.service.ResumeService;
import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUserArgumentResolver;
import com.careeros.common.EnvelopeAdvice;
import com.careeros.common.GlobalExceptionHandler;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.Pageable;
import org.springframework.http.MediaType;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

/**
 * The data-portability routes (Epics 13.1-13.3).
 *
 * <p>The bundle is the user's own data, so two things are worth pinning: the
 * export is scoped to the caller and its anonymized flag reaches the engine as
 * the boolean it is (not as a truthy string), and the redaction route passes
 * the sections to drop through untouched — a name the engine does not know is
 * the engine's to refuse, not the bridge's to swallow.
 */
class DataPortabilityControllerTest {

    private static final String USER = "6b0178a0-d352-09c3-ea65-8f107bd28d01";

    private AiServiceClient ai;
    private ApplicationRepository applications;
    private GrowthPlanRepository growthPlans;
    private UserProfileRepository profiles;
    private UserNoteRepository notes;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        ai = mock(AiServiceClient.class);
        applications = mock(ApplicationRepository.class);
        growthPlans = mock(GrowthPlanRepository.class);
        profiles = mock(UserProfileRepository.class);
        notes = mock(UserNoteRepository.class);
        ExportService exports = new ExportService(ai, applications, growthPlans);
        ImportService imports = new ImportService(ai, profiles, notes, applications, growthPlans,
                mock(ResumeService.class), mock(KnowledgeService.class),
                mock(JobJdRepository.class), mock(JobRepository.class),
                mock(InterviewSessionRepository.class), mock(InterviewTurnRepository.class),
                mock(InterviewEvaluationRepository.class));
        DataPortabilityController controller = new DataPortabilityController(ai, exports, imports);
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
    void the_export_is_the_engines_bundle_wrapped_once() throws Exception {
        when(applications.findByUserIdOrderByUpdatedAtDescIdAsc(eq(UUID.fromString(USER)), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of()));
        when(growthPlans.findByUserIdOrderByCreatedAtDesc(eq(UUID.fromString(USER))))
                .thenReturn(List.of());
        when(ai.exportBundle(eq(UUID.fromString(USER)), anyBoolean(), any()))
                .thenReturn(Map.of("schema_version", "1.1.0",
                        "manifest", Map.of("content_hash", "abc123")));

        mvc.perform(post("/api/v1/data-portability/export")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.schema_version").value("1.1.0"))
                .andExpect(jsonPath("$.data.manifest.content_hash").value("abc123"));

        verify(ai).exportBundle(eq(UUID.fromString(USER)), eq(false), any());
    }

    /**
     * The bundle is complete: the sections the BACKEND owns travel with it, so
     * an export is the candidate's pipeline and not only their reading list.
     */
    @Test
    void the_export_carries_the_sections_the_backend_owns() throws Exception {
        when(applications.findByUserIdOrderByUpdatedAtDescIdAsc(eq(UUID.fromString(USER)), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of()));
        when(growthPlans.findByUserIdOrderByCreatedAtDesc(eq(UUID.fromString(USER))))
                .thenReturn(List.of());
        when(ai.exportBundle(eq(UUID.fromString(USER)), anyBoolean(), any()))
                .thenReturn(Map.of("schema_version", "1.1.0"));

        mvc.perform(post("/api/v1/data-portability/export")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{}"))
                .andExpect(status().isOk());

        @SuppressWarnings("unchecked")
        ArgumentCaptor<Map<String, Object>> sections = ArgumentCaptor.forClass(Map.class);
        verify(ai).exportBundle(eq(UUID.fromString(USER)), eq(false), sections.capture());
        assertThat(sections.getValue()).containsKeys("applications", "growth_plans");
    }

    @Test
    void the_anonymized_flag_reaches_the_engine_as_a_boolean() throws Exception {
        when(applications.findByUserIdOrderByUpdatedAtDescIdAsc(eq(UUID.fromString(USER)), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of()));
        when(growthPlans.findByUserIdOrderByCreatedAtDesc(eq(UUID.fromString(USER))))
                .thenReturn(List.of());
        when(ai.exportBundle(eq(UUID.fromString(USER)), anyBoolean(), any()))
                .thenReturn(Map.of("schema_version", "1.1.0"));

        mvc.perform(post("/api/v1/data-portability/export")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"anonymized\":true}"))
                .andExpect(status().isOk());

        verify(ai).exportBundle(eq(UUID.fromString(USER)), eq(true), any());
    }

    @Test
    void the_import_plan_carries_the_bundle_and_the_existing_state() throws Exception {
        when(ai.importPlan(eq(UUID.fromString(USER)), any(), any()))
                .thenReturn(Map.of("op_counts", Map.of("create", 1, "update", 2, "delete", 0, "total", 3)));

        mvc.perform(post("/api/v1/data-portability/import-plan")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"bundle":{"schema_version":"1.0.0"},
                                 "existing":{"schema_version":"1.0.0"}}
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.op_counts.total").value(3));

        @SuppressWarnings("unchecked")
        ArgumentCaptor<Map<String, Object>> bundle = ArgumentCaptor.forClass(Map.class);
        @SuppressWarnings("unchecked")
        ArgumentCaptor<Map<String, Object>> existing = ArgumentCaptor.forClass(Map.class);
        verify(ai).importPlan(eq(UUID.fromString(USER)), bundle.capture(), existing.capture());
        assertThat(bundle.getValue()).containsKey("schema_version");
        assertThat(existing.getValue()).containsKey("schema_version");
    }

    @Test
    void the_redaction_passes_the_sections_to_drop_through() throws Exception {
        when(ai.redactBundle(eq(UUID.fromString(USER)), any(), any()))
                .thenReturn(Map.of("manifest", Map.of("redacted_sections", List.of("interviews"))));

        mvc.perform(post("/api/v1/data-portability/redact")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"bundle\":{\"schema_version\":\"1.0.0\"},\"drop\":[\"interviews\"]}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.manifest.redacted_sections[0]").value("interviews"));

        @SuppressWarnings("unchecked")
        ArgumentCaptor<List<String>> drop = ArgumentCaptor.forClass(List.class);
        verify(ai).redactBundle(eq(UUID.fromString(USER)), any(), drop.capture());
        assertThat(drop.getValue()).containsExactly("interviews");
    }

    /**
     * A redaction with no sections named is not an error: the caller asked for
     * nothing to be dropped, and the answer is the bundle unchanged.
     */
    @Test
    void a_redaction_with_nothing_to_drop_is_not_an_error() throws Exception {
        when(ai.redactBundle(eq(UUID.fromString(USER)), any(), isNull()))
                .thenReturn(Map.of("schema_version", "1.0.0"));

        mvc.perform(post("/api/v1/data-portability/redact")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"bundle\":{\"schema_version\":\"1.0.0\"}}"))
                .andExpect(status().isOk());

        verify(ai).redactBundle(eq(UUID.fromString(USER)), any(), isNull());
    }

    /**
     * The apply is the write half of the restore: it says what it wrote and
     * which sections it left alone, so a partial restore is visible rather
     * than reported as a success.
     */
    @Test
    void the_apply_reports_what_it_wrote_and_what_it_skipped() throws Exception {
        when(profiles.findByUserId(eq(UUID.fromString(USER)))).thenReturn(java.util.Optional.empty());
        when(applications.findByUserIdOrderByUpdatedAtDescIdAsc(eq(UUID.fromString(USER)), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of()));
        when(growthPlans.findByUserIdOrderByCreatedAtDesc(eq(UUID.fromString(USER))))
                .thenReturn(List.of());
        when(ai.importPlan(eq(UUID.fromString(USER)), any(), any()))
                .thenReturn(Map.of(
                        "op_counts", Map.of("create", 1, "update", 0, "delete", 0, "total", 1),
                        "sections", Map.of(
                                "profile", List.of(Map.of("op", "update", "id", "p1")),
                                "memories", List.of(Map.of("op", "create", "id", "m1")))));

        mvc.perform(post("/api/v1/data-portability/import-apply")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"bundle":{"schema_version":"1.1.0","data":{
                                  "profile":{"headline":"Backend engineer"},
                                  "memories":[{"id":"m1"}]}}}
                                """))
                .andExpect(status().isOk())
                // The profile was written; the memories were not, and the answer
                // says so rather than claiming the whole bundle landed.
                .andExpect(jsonPath("$.data.applied.profile.updated").value(1))
                .andExpect(jsonPath("$.data.skipped[0].section").value("memories"));
    }

    /**
     * A bundle with no data section is not a bundle: the route refuses it
     * before the plan runs.
     */
    @Test
    void an_apply_without_a_data_section_is_refused() throws Exception {
        mvc.perform(post("/api/v1/data-portability/import-apply")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"bundle\":{\"schema_version\":\"1.1.0\"}}"))
                .andExpect(status().isBadRequest());
    }
}
