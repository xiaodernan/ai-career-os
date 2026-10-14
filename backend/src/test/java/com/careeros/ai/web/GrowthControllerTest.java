package com.careeros.ai.web;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.careeros.ai.dto.GrowthReportRequest;
import com.careeros.ai.service.GrowthService;
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
import org.springframework.http.MediaType;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

/**
 * The 10.2 bridge's first route. What is worth pinning here is not the report's shape — the
 * ai-service owns it and pins it over there — but the pass-through contract: the route is
 * user-scoped, the request's camelCase binds to the engine's snake_case body, the optionals
 * stay absent when the caller omitted them (a JSON null is not the same wire fact as a key
 * the engine never received), and the answer crosses the envelope unwrapped.
 */
class GrowthControllerTest {

    private static final String USER = "6b0178a0-d352-09c3-ea65-8f107bd28d01";

    private GrowthService growth;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        growth = mock(GrowthService.class);
        GrowthController controller = new GrowthController(growth);
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
    void the_report_is_the_engines_answer_wrapped_once() throws Exception {
        Map<String, Object> report = Map.of(
                "readiness", Map.of("verdict", "not_ready", "coverage", 0.42),
                "salary", Map.of("p50", 420000));
        when(growth.report(eq(UUID.fromString(USER)), any(GrowthReportRequest.class)))
                .thenReturn(report);

        mvc.perform(post("/api/v1/growth-report")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"targetRole":"Senior Backend Engineer (Java)",
                                 "seniority":"senior","location":"Shanghai","currency":"CNY",
                                 "targetSalary":500000}
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.readiness.verdict").value("not_ready"))
                .andExpect(jsonPath("$.data.salary.p50").value(420000));

        ArgumentCaptor<GrowthReportRequest> sent = ArgumentCaptor.forClass(GrowthReportRequest.class);
        verify(growth).report(eq(UUID.fromString(USER)), sent.capture());
        assertThat(sent.getValue().targetRole()).isEqualTo("Senior Backend Engineer (Java)");
        assertThat(sent.getValue().seniority()).isEqualTo("senior");
        assertThat(sent.getValue().location()).isEqualTo("Shanghai");
        assertThat(sent.getValue().targetSalary()).isEqualTo(500000);
        // The caller sent no resume version and no previous report; the bridge must not
        // manufacture empty strings where the engine expects absence.
        assertThat(sent.getValue().resumeVersionId()).isNull();
        assertThat(sent.getValue().previous()).isNull();
    }

    @Test
    void a_target_role_below_the_engine_floor_is_refused_before_the_call() throws Exception {
        mvc.perform(post("/api/v1/growth-report")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"targetRole\":\"Chef\"}"))
                .andExpect(status().isBadRequest());

        org.mockito.Mockito.verifyNoInteractions(growth);
    }

    @Test
    void an_unauthenticated_call_is_refused_by_the_framework_not_the_client() throws Exception {
        SecurityContextHolder.clearContext();
        mvc.perform(post("/api/v1/growth-report")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"targetRole\":\"Senior Backend Engineer\"}"))
                .andExpect(status().isUnauthorized());
    }
}
