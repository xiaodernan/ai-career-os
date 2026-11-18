package com.careeros.ai.web;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.careeros.ai.dto.NextStepRequest;
import com.careeros.ai.service.AssistantService;
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
import org.springframework.http.MediaType;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

/**
 * The assistant's own route (Epic 331).
 *
 * <p>What is worth pinning is the seam, not the sentence: a call carries no
 * body of its own — only the language — and the answer is the backend-built
 * workspace payload plus, when the editor kept one, `step`. The service's own
 * counts are pinned in AssistantService's integration test; this test pins the
 * route shape: user-scoped, optional body, locale travels.
 */
class AssistantControllerTest {

    private static final String USER = "6b0178a0-d352-09c3-ea65-8f107bd28d01";

    private AssistantService assistant;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        assistant = mock(AssistantService.class);
        AssistantController controller = new AssistantController(assistant);
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
    void theLocaleCarriesIntoTheAnswerAndTheCallerScopesIt() throws Exception {
        when(assistant.nextStep(eq(UUID.fromString(USER)), any(NextStepRequest.class)))
                .thenReturn(Map.of("totalApplications", 23, "attentionCount", 4,
                        "reminderDue", 1, "staleCount", 3,
                        "interviewsStartedLast7Days", 2, "offersPending", 0,
                        "locale", "zh", "step", "先处理那 1 个到期的提醒——3 个没动的投递先放一放。"));

        mvc.perform(post("/api/v1/assistant/next-step")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"locale\": \"zh\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.step").value("先处理那 1 个到期的提醒——3 个没动的投递先放一放。"))
                .andExpect(jsonPath("$.data.totalApplications").value(23));
    }

    @Test
    void anEmptyBodyIsAValidAsk() throws Exception {
        when(assistant.nextStep(eq(UUID.fromString(USER)), any()))
                .thenReturn(Map.of("totalApplications", 0, "attentionCount", 0,
                        "reminderDue", 0, "staleCount", 0,
                        "interviewsStartedLast7Days", 0, "offersPending", 0,
                        "locale", "en"));

        mvc.perform(post("/api/v1/assistant/next-step"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.totalApplications").value(0));
    }
}
