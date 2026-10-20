package com.careeros.ai.web;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.careeros.ai.dto.GrowthEngineRequest;
import com.careeros.ai.dto.ProfileEngineRequest;
import com.careeros.ai.service.GrowthEngineService;
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
 * The granular growth engines, each on its own route (Epics 10.1-10.13).
 *
 * <p>What is worth pinning is the pass-through contract, not the answers' shapes —
 * the ai-service owns those and pins them over there. Three things have to hold:
 * every route is user-scoped; the camelCase request binds to the record the
 * engine's body is built from; and the optionals stay <em>absent</em> when the
 * caller omitted them, because a JSON null is not the same wire fact as a key
 * the engine never received.
 *
 * <p>The two profile-anchored engines take a different record on purpose: they
 * read no target role, so a request naming one would be a request that lies
 * about what it asked. The last two tests hold that difference in place.
 */
class GrowthEngineControllerTest {

    private static final String USER = "6b0178a0-d352-09c3-ea65-8f107bd28d01";

    private GrowthEngineService growth;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        growth = mock(GrowthEngineService.class);
        GrowthEngineController controller = new GrowthEngineController(growth);
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
    void the_gap_analysis_is_the_engines_answer_wrapped_once() throws Exception {
        when(growth.gapAnalysis(eq(UUID.fromString(USER)), any(GrowthEngineRequest.class)))
                .thenReturn(Map.of("targetRole", "Senior Backend Engineer (Java)", "coverage", 0.42));

        mvc.perform(post("/api/v1/growth/gap-analysis")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"targetRole":"Senior Backend Engineer (Java)",
                                 "seniority":"senior","resumeVersionId":"11111111-1111-1111-1111-111111111111"}
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.targetRole").value("Senior Backend Engineer (Java)"))
                .andExpect(jsonPath("$.data.coverage").value(0.42));

        ArgumentCaptor<GrowthEngineRequest> sent = ArgumentCaptor.forClass(GrowthEngineRequest.class);
        verify(growth).gapAnalysis(eq(UUID.fromString(USER)), sent.capture());
        assertThat(sent.getValue().targetRole()).isEqualTo("Senior Backend Engineer (Java)");
        assertThat(sent.getValue().seniority()).isEqualTo("senior");
        assertThat(sent.getValue().resumeVersionId()).isEqualTo("11111111-1111-1111-1111-111111111111");
        // The caller sent no location and no salary target; the bridge must not
        // manufacture empty strings where the engine expects absence.
        assertThat(sent.getValue().location()).isNull();
        assertThat(sent.getValue().targetSalary()).isNull();
    }

    @Test
    void a_target_role_below_the_engine_floor_is_refused_before_the_call() throws Exception {
        mvc.perform(post("/api/v1/growth/gap-analysis")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"targetRole\":\"Chef\"}"))
                .andExpect(status().isBadRequest());

        verifyNoInteractions(growth);
    }

    /**
     * The demand engine names the role it is asking about differently, so the
     * record it binds is the one that says "role", not "targetRole".
     */
    @Test
    void the_skill_demand_asks_about_a_role_family_not_a_target_role() throws Exception {
        when(growth.skillDemand(eq(UUID.fromString(USER)), any(GrowthEngineRequest.class)))
                .thenReturn(Map.of("skills", List.of(Map.of("name", "Kubernetes", "count", 12))));

        mvc.perform(post("/api/v1/growth/skill-demand")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"targetRole\":\"Backend Engineer (Java)\",\"top\":5}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.skills[0].name").value("Kubernetes"));

        ArgumentCaptor<GrowthEngineRequest> sent = ArgumentCaptor.forClass(GrowthEngineRequest.class);
        verify(growth).skillDemand(eq(UUID.fromString(USER)), sent.capture());
        assertThat(sent.getValue().top()).isEqualTo(5);
    }

    /**
     * The two profile-anchored engines take the profile record, so a body that
     * names a target role has nowhere to put it: Jackson ignores the unknown
     * key, and the engine is asked exactly what it reads.
     */
    @Test
    void the_story_bank_asks_about_the_profile_and_not_about_a_target_role() throws Exception {
        when(growth.storyBank(eq(UUID.fromString(USER)), any(ProfileEngineRequest.class)))
                .thenReturn(Map.of("stories", List.of(Map.of("title", "Payments rewrite"))));

        mvc.perform(post("/api/v1/growth/story-bank")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"resumeVersionId\":\"11111111-1111-1111-1111-111111111111\",\"top\":3}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.stories[0].title").value("Payments rewrite"));

        ArgumentCaptor<ProfileEngineRequest> sent = ArgumentCaptor.forClass(ProfileEngineRequest.class);
        verify(growth).storyBank(eq(UUID.fromString(USER)), sent.capture());
        assertThat(sent.getValue().resumeVersionId()).isEqualTo("11111111-1111-1111-1111-111111111111");
        assertThat(sent.getValue().top()).isEqualTo(3);
    }

    @Test
    void an_unauthenticated_call_is_refused_by_the_framework_not_the_client() throws Exception {
        SecurityContextHolder.clearContext();
        mvc.perform(post("/api/v1/growth/readiness")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"targetRole\":\"Senior Backend Engineer\"}"))
                .andExpect(status().isUnauthorized());
    }
}
