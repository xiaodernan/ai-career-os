package com.careeros.job.web;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.careeros.ai.AiServiceClient;
import com.careeros.application.service.ApplicationService;
import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUserArgumentResolver;
import com.careeros.common.EnvelopeAdvice;
import com.careeros.common.GlobalExceptionHandler;
import com.careeros.job.entity.Job;
import com.careeros.job.entity.JobJd;
import com.careeros.job.repository.CompanyRepository;
import com.careeros.job.repository.JobJdRepository;
import com.careeros.job.repository.JobMatchRepository;
import com.careeros.job.repository.JobRepository;
import com.careeros.job.repository.JobSearchRepository;
import com.careeros.job.repository.SavedJobRepository;
import com.careeros.job.service.JobService;
import com.careeros.resume.service.ResumeService;
import com.careeros.search.service.QueryEmbeddingService;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.http.MediaType;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

/**
 * The three JD routes (/api/v1/jds) had no controller-level test before this file: grep for
 * "jds" under backend/src/test returned only the rate-limit filter's parameter list.
 *
 * What the standalone setup holds that the service tests do not: the transport contract
 * (201 vs 200, the envelope's data shape, the snake_case JSON aliases the frontend actually
 * sends) and the ownership scoping of GET /jds/{id} — {@code requireJd} answers "not yours"
 * and "not there" with the same 404, and nothing until now proved that answer reaches the
 * wire as a 404 rather than a 500. The service-side link behaviour stays in
 * JobServiceLinkTest; this file holds the HTTP half of the same routes.
 */
class JdControllerTest {

    private static final UUID ALICE = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final UUID JOB = UUID.fromString("22222222-2222-4222-8222-222222222222");
    private static final UUID JD = UUID.fromString("33333333-3333-4333-8333-333333333333");
    private static final UUID RV = UUID.fromString("44444444-4444-4444-8444-444444444444");

    private JobRepository jobs;
    private JobJdRepository jds;
    private AiServiceClient ai;
    private ApplicationService applications;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        jobs = mock(JobRepository.class);
        jds = mock(JobJdRepository.class);
        ai = mock(AiServiceClient.class);
        applications = mock(ApplicationService.class);
        JobService service = new JobService(jobs, mock(CompanyRepository.class), jds,
                mock(SavedJobRepository.class), mock(JobMatchRepository.class),
                mock(JobSearchRepository.class), mock(ResumeService.class), applications,
                ai, mock(QueryEmbeddingService.class));
        mvc = MockMvcBuilders.standaloneSetup(new JdController(service))
                .setControllerAdvice(new EnvelopeAdvice(), new GlobalExceptionHandler())
                .setCustomArgumentResolvers(new CurrentUserArgumentResolver())
                .build();
        as(ALICE);
        Job job = new Job();
        ReflectionTestUtils.setField(job, "id", JOB);
        when(jobs.findById(JOB)).thenReturn(Optional.of(job));
    }

    @AfterEach
    void clearPrincipal() {
        SecurityContextHolder.clearContext();
    }

    private static void as(UUID id) {
        SecurityContextHolder.getContext().setAuthentication(new UsernamePasswordAuthenticationToken(
                new AuthUser(id, "ada@example.invalid", "user"), null, List.of()));
    }

    private JobJd savedJd() {
        JobJd jd = new JobJd();
        ReflectionTestUtils.setField(jd, "id", JD);
        return jd;
    }

    // --------------------------------- analyze ----------------------------------

    @Test
    void analyze_answers_201_with_the_mapped_item() throws Exception {
        when(ai.analyzeJd(eq("raw jd text"), eq(ALICE)))
                .thenReturn(new HashMap<>(Map.of("parsed", Map.of("title", "Backend"))));
        when(jds.save(any())).thenAnswer(inv -> {
            JobJd jd = inv.getArgument(0);
            ReflectionTestUtils.setField(jd, "id", JD);
            return jd;
        });

        mvc.perform(post("/api/v1/jds").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"rawText\":\"raw jd text\"}"))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.data.id").value(JD.toString()))
                .andExpect(jsonPath("$.data.rawText").value("raw jd text"))
                .andExpect(jsonPath("$.data.jobId").doesNotExist());
    }

    @Test
    void analyze_scopes_the_ai_call_and_the_row_to_the_principal() throws Exception {
        when(ai.analyzeJd(any(), any()))
                .thenReturn(new HashMap<>(Map.of("parsed", Map.of())));
        // The controller maps the saved row, so an unstubbed save answers null and the mapping
        // turns into a 500; every analyze test needs the id-setting answer, not only the ones
        // that assert the response body.
        when(jds.save(any())).thenAnswer(inv -> {
            JobJd jd = inv.getArgument(0);
            ReflectionTestUtils.setField(jd, "id", JD);
            return jd;
        });
        ArgumentCaptor<String> text = ArgumentCaptor.forClass(String.class);
        ArgumentCaptor<JobJd> row = ArgumentCaptor.forClass(JobJd.class);

        mvc.perform(post("/api/v1/jds").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"rawText\":\"raw jd text\"}"))
                .andExpect(status().isCreated());

        verify(ai).analyzeJd(text.capture(), eq(ALICE));
        org.assertj.core.api.Assertions.assertThat(text.getValue()).isEqualTo("raw jd text");
        verify(jds).save(row.capture());
        org.assertj.core.api.Assertions.assertThat(row.getValue().getUserId()).isEqualTo(ALICE);
    }

    @Test
    void analyze_with_a_job_links_the_analysis_to_the_tracker_row() throws Exception {
        when(ai.analyzeJd(any(), any()))
                .thenReturn(new HashMap<>(Map.of("parsed", Map.of())));
        when(jds.save(any())).thenAnswer(inv -> {
            // The argument must be typed before setField: a bare inv.getArgument(0)
            // lets the compiler infer setField(Class, ...) -- Class is more specific
            // than Object -- and the runtime JobJd is then cast to Class.
            JobJd jd = inv.getArgument(0);
            ReflectionTestUtils.setField(jd, "id", JD);
            return jd;
        });

        mvc.perform(post("/api/v1/jds").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"rawText\":\"raw jd text\",\"jobId\":\"" + JOB + "\"}"))
                .andExpect(status().isCreated());

        verify(applications).linkJobActivity(ALICE, JOB, null, JD, null);
    }

    @Test
    void analyze_without_a_job_links_nothing() throws Exception {
        when(ai.analyzeJd(any(), any()))
                .thenReturn(new HashMap<>(Map.of("parsed", Map.of())));
        when(jds.save(any())).thenAnswer(inv -> {
            // The argument must be typed before setField: a bare inv.getArgument(0)
            // lets the compiler infer setField(Class, ...) -- Class is more specific
            // than Object -- and the runtime JobJd is then cast to Class.
            JobJd jd = inv.getArgument(0);
            ReflectionTestUtils.setField(jd, "id", JD);
            return jd;
        });

        mvc.perform(post("/api/v1/jds").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"rawText\":\"raw jd text\"}"))
                .andExpect(status().isCreated());

        verify(applications, never()).linkJobActivity(any(), any(), any(), any(), any());
    }

    @Test
    void analyze_of_a_job_the_user_cannot_reach_is_404_before_the_ai_is_called()
            throws Exception {
        when(jobs.findById(JOB)).thenReturn(Optional.empty());

        mvc.perform(post("/api/v1/jds").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"rawText\":\"raw jd text\",\"jobId\":\"" + JOB + "\"}"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error.code").value("JOB_NOT_FOUND"));

        verifyNoInteractions(ai);
        verify(jds, never()).save(any());
    }

    @Test
    void analyze_rejects_blank_raw_text() throws Exception {
        mvc.perform(post("/api/v1/jds").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"rawText\":\"  \"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("VALIDATION_FAILED"))
                .andExpect(jsonPath("$.error.details[0].field").value("rawText"));

        verifyNoInteractions(ai);
    }

    @Test
    void analyze_accepts_the_snake_case_aliases_the_frontend_sends() throws Exception {
        when(ai.analyzeJd(any(), any()))
                .thenReturn(new HashMap<>(Map.of("parsed", Map.of())));
        when(jds.save(any())).thenAnswer(inv -> {
            // The argument must be typed before setField: a bare inv.getArgument(0)
            // lets the compiler infer setField(Class, ...) -- Class is more specific
            // than Object -- and the runtime JobJd is then cast to Class.
            JobJd jd = inv.getArgument(0);
            ReflectionTestUtils.setField(jd, "id", JD);
            return jd;
        });

        mvc.perform(post("/api/v1/jds").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"raw_text\":\"raw jd text\",\"job_id\":\"" + JOB + "\"}"))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.data.id").value(JD.toString()));
    }

    // ----------------------------------- get ------------------------------------

    @Test
    void get_returns_the_owner_item() throws Exception {
        JobJd jd = savedJd();
        jd.setUserId(ALICE);
        jd.setRawText("raw jd text");
        when(jds.findByIdAndUserId(JD, ALICE)).thenReturn(Optional.of(jd));

        mvc.perform(get("/api/v1/jds/" + JD))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.id").value(JD.toString()))
                .andExpect(jsonPath("$.data.rawText").value("raw jd text"));
    }

    @Test
    void get_of_a_foreign_jd_is_404_not_403_and_not_500() throws Exception {
        when(jds.findByIdAndUserId(JD, ALICE)).thenReturn(Optional.empty());

        mvc.perform(get("/api/v1/jds/" + JD))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error.code").value("JD_NOT_FOUND"));
    }

    @Test
    void get_rejects_a_malformed_id() throws Exception {
        mvc.perform(get("/api/v1/jds/not-a-uuid"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("MALFORMED_REQUEST"));
    }

    // -------------------------------- suggestions --------------------------------

    @Test
    void suggestions_passes_body_and_principal_through_to_the_client() throws Exception {
        Map<String, Object> upstream = Map.of("keywords", List.of("Kafka"));
        when(ai.jdSuggestions(eq(RV), eq("jd raw"), eq(ALICE))).thenReturn(upstream);

        mvc.perform(post("/api/v1/jds/suggestions").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"resumeVersionId\":\"" + RV + "\",\"jdRaw\":\"jd raw\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.keywords[0]").value("Kafka"));
    }

    @Test
    void suggestions_rejects_blank_jd_raw() throws Exception {
        mvc.perform(post("/api/v1/jds/suggestions").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"jdRaw\":\" \"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("VALIDATION_FAILED"))
                .andExpect(jsonPath("$.error.details[0].field").value("jdRaw"));

        verifyNoInteractions(ai);
    }

    @Test
    void suggestions_accepts_the_snake_case_aliases() throws Exception {
        when(ai.jdSuggestions(eq(RV), eq("jd raw"), eq(ALICE))).thenReturn(Map.of());

        mvc.perform(post("/api/v1/jds/suggestions").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"resume_version_id\":\"" + RV + "\",\"jd_raw\":\"jd raw\"}"))
                .andExpect(status().isOk());
    }

    // ---------------------------------- auth ------------------------------------

    @Test
    void every_route_requires_authentication() throws Exception {
        SecurityContextHolder.clearContext();
        mvc.perform(post("/api/v1/jds").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"rawText\":\"x\"}"))
                .andExpect(status().isUnauthorized());
        mvc.perform(get("/api/v1/jds/" + JD))
                .andExpect(status().isUnauthorized());
        mvc.perform(post("/api/v1/jds/suggestions").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"jdRaw\":\"x\"}"))
                .andExpect(status().isUnauthorized());
    }
}
