package com.careeros.job.web;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUserArgumentResolver;
import com.careeros.common.EnvelopeAdvice;
import com.careeros.common.GlobalExceptionHandler;
import com.careeros.job.service.JobService;
import com.careeros.resume.dto.ResumeDtos.ResumeVersionItem;
import com.careeros.resume.dto.ResumeDtos.TailoredVersionRequest;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

/**
 * "Save as version" is the one write in this repo whose URL, body and response shape are each
 * stated in a different language: the panel posts to a hand-copied path, builds the body in
 * {@code tailorSaveBody}, and reads {@code data.label} out of the reply. Everything unit-tested
 * so far constructed the request record in Java, so nothing proved the shipped JSON reaches it —
 * or that the route answers at all. This drives the real MVC pipeline with that exact payload.
 *
 * <p>Standalone setup deliberately reuses the production advice and argument resolver rather than
 * Spring Security's test glue, so the envelope the client unwraps and the {@code @CurrentUser}
 * the service scopes by are the same objects the running app installs.
 */
class JobControllerTailoredVersionTest {

    private static final UUID USER = UUID.fromString("11111111-1111-1111-1111-111111111111");
    private static final UUID RESUME = UUID.fromString("22222222-2222-2222-2222-222222222222");
    private static final UUID JOB = UUID.fromString("33333333-3333-3333-3333-333333333333");
    private static final UUID BASE_VERSION = UUID.fromString("44444444-4444-4444-4444-444444444444");
    private static final UUID NEW_VERSION = UUID.fromString("55555555-5555-5555-5555-555555555555");

    /** Exactly what {@code tailorSaveBody} sends now: each field once, camelCase throughout. */
    private static final String CLIENT_BODY = """
            {
              "tailored": {
                "profile": {"name": "Ada Lovelace", "title": "Backend Engineer"},
                "experience": [{"company": "ACME", "bullets": ["Shipped the ingest pipeline"]}]
              },
              "diff": {"accepted": [{"path": "experience.0.bullets.0"}], "rejected": []},
              "plaintext": "# Ada Lovelace\\n\\nBackend Engineer",
              "resumeVersionId": "44444444-4444-4444-4444-444444444444"
            }
            """;

    /** The same body with the alias twin restored — the shape every AI action used to post. */
    private static final String DUAL_SPELLING_BODY = """
            {
              "tailored": {"profile": {"name": "Ada Lovelace"}},
              "diff": {"accepted": []},
              "plaintext": "# Ada Lovelace",
              "resumeVersionId": "44444444-4444-4444-4444-444444444444",
              "resume_version_id": "44444444-4444-4444-4444-444444444444"
            }
            """;

    private JobService jobs;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        jobs = mock(JobService.class);
        SecurityContextHolder.getContext().setAuthentication(new UsernamePasswordAuthenticationToken(
                new AuthUser(USER, "ada@example.invalid", "user"), null, List.of()));
        mvc = MockMvcBuilders.standaloneSetup(new JobController(jobs))
                .setControllerAdvice(new EnvelopeAdvice(), new GlobalExceptionHandler())
                .setCustomArgumentResolvers(new CurrentUserArgumentResolver())
                .build();
    }

    @AfterEach
    void clearPrincipal() {
        SecurityContextHolder.clearContext();
    }

    private void stubSavedVersion() {
        when(jobs.saveTailored(any(), any(), any())).thenReturn(new ResumeVersionItem(
                NEW_VERSION, RESUME, "tailored-" + JOB.toString().substring(0, 8) + "-2", "tailored",
                JOB, OffsetDateTime.of(2026, 9, 20, 8, 0, 0, 0, ZoneOffset.UTC),
                Map.of("accepted", List.of(Map.of("path", "experience.0.bullets.0")))));
    }

    private TailoredVersionRequest capturedRequest() {
        ArgumentCaptor<TailoredVersionRequest> captor =
                ArgumentCaptor.forClass(TailoredVersionRequest.class);
        verify(jobs).saveTailored(any(), any(), captor.capture());
        return captor.getValue();
    }

    @Test
    void theRouteThePanelPostsToAnswersCreated() throws Exception {
        stubSavedVersion();

        mvc.perform(post("/api/v1/jobs/{id}/tailored-version", JOB)
                        .contentType("application/json").content(CLIENT_BODY))
                .andExpect(status().isCreated());
    }

    @Test
    void oneFieldUnderBothSpellingsIsRefusedAsTheCallersMistakeNotOurs() throws Exception {
        // Jackson aborts binding with HttpMessageConversionException. It used to fall through to
        // the catch-all and answer 500 — a server-error toast for what is a bad request body —
        // which is also how five AI actions failed for months while their unit tests stayed green.
        mvc.perform(post("/api/v1/jobs/{id}/tailored-version", JOB)
                        .contentType("application/json").content(DUAL_SPELLING_BODY))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("MALFORMED_REQUEST"));

        verify(jobs, never()).saveTailored(any(), any(), any());
    }

    @Test
    void theStructuredBodySurvivesTheWireAndReachesTheService() throws Exception {
        stubSavedVersion();

        mvc.perform(post("/api/v1/jobs/{id}/tailored-version", JOB)
                        .contentType("application/json").content(CLIENT_BODY))
                .andExpect(status().isCreated());

        TailoredVersionRequest sent = capturedRequest();
        assertThat(sent.resumeVersionId()).isEqualTo(BASE_VERSION);
        assertThat(sent.tailored()).containsKey("profile");
        @SuppressWarnings("unchecked")
        Map<String, Object> profile = (Map<String, Object>) sent.tailored().get("profile");
        assertThat(profile).containsEntry("title", "Backend Engineer");
        assertThat(sent.tailored().get("experience")).isInstanceOf(List.class);
        assertThat(sent.diff()).containsKey("accepted");
        assertThat(sent.plaintext()).startsWith("# Ada Lovelace");
    }

    @Test
    void theOwnerComesFromTheTokenAndTheJobFromThePath() throws Exception {
        stubSavedVersion();

        mvc.perform(post("/api/v1/jobs/{id}/tailored-version", JOB)
                        .contentType("application/json").content(CLIENT_BODY))
                .andExpect(status().isCreated());

        ArgumentCaptor<UUID> owner = ArgumentCaptor.forClass(UUID.class);
        ArgumentCaptor<UUID> jobId = ArgumentCaptor.forClass(UUID.class);
        ArgumentCaptor<TailoredVersionRequest> body = ArgumentCaptor.forClass(TailoredVersionRequest.class);
        verify(jobs).saveTailored(owner.capture(), jobId.capture(), body.capture());

        assertThat(owner.getValue()).isEqualTo(USER);
        assertThat(jobId.getValue()).isEqualTo(JOB);
        // Nothing in the body names a user: a client cannot move the write into someone else's
        // resume tree, so an argument order swap here is a tenant bug, not a typo.
        assertThat(body.getValue().resumeVersionId()).isEqualTo(BASE_VERSION);
    }

    @Test
    void theLabelTheBadgePrintsIsInTheEnvelopeTheClientUnwraps() throws Exception {
        stubSavedVersion();

        mvc.perform(post("/api/v1/jobs/{id}/tailored-version", JOB)
                        .contentType("application/json").content(CLIENT_BODY))
                .andExpect(jsonPath("$.data.label").value("tailored-" + JOB.toString().substring(0, 8) + "-2"))
                .andExpect(jsonPath("$.data.kind").value("tailored"))
                .andExpect(jsonPath("$.data.id").value(NEW_VERSION.toString()))
                .andExpect(jsonPath("$.data.diff.accepted[0].path").value("experience.0.bullets.0"));
    }

    @Test
    void anAnonymousSaveIsRefusedBeforeTheWrite() throws Exception {
        SecurityContextHolder.clearContext();

        mvc.perform(post("/api/v1/jobs/{id}/tailored-version", JOB)
                        .contentType("application/json").content(CLIENT_BODY))
                .andExpect(status().isUnauthorized());

        verify(jobs, never()).saveTailored(any(), any(), any());
    }
}
