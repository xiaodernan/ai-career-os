package com.careeros.resume.web;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUserArgumentResolver;
import com.careeros.common.EnvelopeAdvice;
import com.careeros.common.GlobalExceptionHandler;
import com.careeros.resume.dto.ResumeDtos.ResumeVersionItem;
import com.careeros.resume.service.ResumeService;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.http.converter.json.MappingJackson2HttpMessageConverter;
import org.springframework.http.converter.json.Jackson2ObjectMapperBuilder;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.util.UriComponentsBuilder;

/**
 * The resume-version routes. The version list feeds the versions panel beside a resume, and
 * the version detail reads the metadata one tailored draft carries. DomainApiIT pins the
 * resume routes themselves but never touched these two — the only paths in the codebase that
 * answer a version by id, and the two that must scope that id to the caller.
 *
 * The controller is a pass-through, so the stub client is the point of the test: the ids it
 * is handed must be the principal's, and the service's NOT_FOUND (a version belonging to
 * somebody else) must travel to the browser as 404 rather than 500/403 — "not yours" and
 * "not there" being the same answer, the same ownership rule the other /me surfaces follow.
 */
class ResumeVersionControllerTest {

    private static final UUID ALICE = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final UUID RESUME = UUID.fromString("22222222-2222-4222-4222-222222222222");
    private static final UUID VERSION = UUID.fromString("44444444-4444-4444-4444-444444444444");

    private ResumeService resumes;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        resumes = mock(ResumeService.class);
        // The converter Spring Boot's auto-configuration builds for MVC, which TimestampWireFormatIT
        // proves answers OffsetDateTime as an ISO-8601 string (the app's own mapper disables
        // WRITE_DATES_AS_TIMESTAMPS). MockMvc's default mapper writes an epoch number instead,
        // so a test asserting what production sends needs the feature off here too.
        MappingJackson2HttpMessageConverter dates = new MappingJackson2HttpMessageConverter(
                Jackson2ObjectMapperBuilder.json()
                        .featuresToDisable(
                                com.fasterxml.jackson.databind.SerializationFeature.WRITE_DATES_AS_TIMESTAMPS)
                        .build());
        mvc = MockMvcBuilders.standaloneSetup(new ResumeVersionController(resumes))
                .setControllerAdvice(new EnvelopeAdvice(), new GlobalExceptionHandler())
                .setCustomArgumentResolvers(new CurrentUserArgumentResolver())
                .setMessageConverters(dates)
                .build();
        as(ALICE);
    }

    @AfterEach
    void clearPrincipal() {
        SecurityContextHolder.clearContext();
    }

    private static void as(UUID id) {
        SecurityContextHolder.getContext().setAuthentication(new UsernamePasswordAuthenticationToken(
                new AuthUser(id, "ada@example.invalid", "user"), null, List.of()));
    }

    private static ResumeVersionItem version() {
        return new ResumeVersionItem(VERSION, RESUME, "v2", "tailored",
                UUID.fromString("66666666-6666-6666-6666-666666666666"),
                OffsetDateTime.parse("2026-10-01T10:00:00Z"),
                java.util.Map.of("changed", java.util.List.of("summary")),
                java.util.Map.of("overall", 78));
    }

    // ------------------------------------------------------------ the list

    @Test
    void the_version_list_is_scoped_to_the_principal_and_answers_bare() throws Exception {
        when(resumes.listVersions(ALICE, RESUME)).thenReturn(java.util.List.of(version()));

        mvc.perform(get("/api/v1/resume-versions").param("resumeId", RESUME.toString()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data[0].id").value(VERSION.toString()))
                .andExpect(jsonPath("$.data[0].label").value("v2"))
                .andExpect(jsonPath("$.data[0].kind").value("tailored"))
                .andExpect(jsonPath("$.data[0].createdAt").value("2026-10-01T10:00:00Z"))
                .andExpect(jsonPath("$.data[0].score.overall").value(78));

        ArgumentCaptor<UUID> user = ArgumentCaptor.forClass(UUID.class);
        verify(resumes).listVersions(user.capture(), eq(RESUME));
        assertThat(user.getValue()).isEqualTo(ALICE);
    }

    @Test
    void the_version_list_of_a_foreign_resume_is_the_services_404() throws Exception {
        // A resume the principal does not own: ResumeService.listVersions calls requireResume
        // first, which answers NOT_FOUND, and the advice renders it as 404. The browser must
        // learn the same thing whether the resume is missing or not theirs.
        when(resumes.listVersions(ALICE, RESUME))
                .thenThrow(new ApiException(ApiErrorCode.NOT_FOUND, "Resume not found"));

        mvc.perform(get("/api/v1/resume-versions").param("resumeId", RESUME.toString()))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error.code").value("NOT_FOUND"));
    }

    @Test
    void the_list_route_demands_a_resume_id() throws Exception {
        // resumeId is required: without it Spring answers 400 before the service runs.
        mvc.perform(get("/api/v1/resume-versions"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("MALFORMED_REQUEST"));

        verifyNoInteractions(resumes);
    }

    // ------------------------------------------------------------ the detail

    @Test
    void a_version_by_id_carries_its_diff_and_score() throws Exception {
        when(resumes.versionMeta(ALICE, VERSION)).thenReturn(version());

        mvc.perform(get("/api/v1/resume-versions/" + VERSION))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.id").value(VERSION.toString()))
                .andExpect(jsonPath("$.data.diff.changed[0]").value("summary"))
                .andExpect(jsonPath("$.data.score.overall").value(78));

        ArgumentCaptor<UUID> user = ArgumentCaptor.forClass(UUID.class);
        verify(resumes).versionMeta(user.capture(), eq(VERSION));
        assertThat(user.getValue()).isEqualTo(ALICE);
    }

    @Test
    void a_version_belonging_to_another_user_is_the_same_404() throws Exception {
        when(resumes.versionMeta(ALICE, VERSION))
                .thenThrow(new ApiException(ApiErrorCode.NOT_FOUND, "Resume version not found"));

        mvc.perform(get("/api/v1/resume-versions/" + VERSION))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error.message").value("Resume version not found"));
    }

    @Test
    void a_malformed_version_id_is_a_framework_400() throws Exception {
        mvc.perform(get("/api/v1/resume-versions/not-a-uuid"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("MALFORMED_REQUEST"));

        verifyNoInteractions(resumes);
    }

    @Test
    void an_unauthenticated_caller_is_refused_before_the_service_runs() throws Exception {
        SecurityContextHolder.clearContext();

        mvc.perform(get("/api/v1/resume-versions").param("resumeId", RESUME.toString()))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.error.code").value("UNAUTHORIZED"));
        mvc.perform(get("/api/v1/resume-versions/" + VERSION))
                .andExpect(status().isUnauthorized());

        verifyNoInteractions(resumes);
    }

    @Test
    void the_caller_id_is_the_principal_and_never_a_query_parameter() throws Exception {
        // The ownership rule stated where it is verifiable: no query parameter can name the
        // user whose versions come back. A URL with `?userId=...` would be ignored entirely.
        when(resumes.listVersions(ALICE, RESUME)).thenReturn(java.util.List.of());

        String url = UriComponentsBuilder.fromPath("/api/v1/resume-versions")
                .queryParam("resumeId", RESUME)
                .queryParam("userId", "99999999-9999-4999-8999-999999999999")
                .build().toUriString();

        mvc.perform(get(url)).andExpect(status().isOk());

        ArgumentCaptor<UUID> scoped = ArgumentCaptor.forClass(UUID.class);
        verify(resumes).listVersions(scoped.capture(), eq(RESUME));
        assertThat(scoped.getValue()).isEqualTo(ALICE);
    }
}
