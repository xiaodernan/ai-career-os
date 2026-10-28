package com.careeros.interview.web;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.careeros.ai.AiServiceClient;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUserArgumentResolver;
import com.careeros.common.EnvelopeAdvice;
import com.careeros.common.GlobalExceptionHandler;
import com.careeros.interview.service.InterviewService;
import com.careeros.interview.service.VoiceService;
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
 * The interview's voice seam (19.6): whether the deployment can listen and
 * speak, one answer transcribed, one question spoken.
 *
 * <p>The service runs for real here against a mocked bridge, so what is under
 * test is the seam's own rules: the state route never fails the page, a
 * foreign session is a 404 before any speech is bought, and a provider that
 * answers nothing is an empty answer rather than a silent success the page
 * would render as a blank transcript.
 */
class VoiceControllerTest {

    private static final UUID ALICE = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final UUID SESSION = UUID.fromString("33333333-3333-4333-8333-333333333333");

    private AiServiceClient ai;
    private InterviewService interviews;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        ai = mock(AiServiceClient.class);
        interviews = mock(InterviewService.class);
        mvc = MockMvcBuilders.standaloneSetup(new VoiceController(new VoiceService(ai, interviews)))
                .setControllerAdvice(new EnvelopeAdvice(), new GlobalExceptionHandler())
                .setCustomArgumentResolvers(new CurrentUserArgumentResolver())
                .build();
        SecurityContextHolder.getContext().setAuthentication(new UsernamePasswordAuthenticationToken(
                new AuthUser(ALICE, "ada@example.invalid", "user"), null, List.of()));
    }

    @AfterEach
    void clearPrincipal() {
        SecurityContextHolder.clearContext();
    }

    @Test
    void theStateRouteNamesTheProviderWhenTheDeploymentHasOne() throws Exception {
        when(ai.voiceState(ALICE)).thenReturn(Map.of(
                "provider", "mock", "stt", true, "tts", true));

        mvc.perform(get("/api/v1/interview/voice"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.provider").value("mock"))
                .andExpect(jsonPath("$.data.stt").value(true))
                .andExpect(jsonPath("$.data.tts").value(true));
    }

    @Test
    void aDeploymentThatCannotAnswerLeavesThePageItsBrowserVoices() throws Exception {
        // The page still runs an interview when this route fails: "cannot ask"
        // and "no provider" are the same answer, and neither is a 5xx the
        // browser would have to catch to show the text box.
        when(ai.voiceState(ALICE)).thenThrow(
                new ApiException(ApiErrorCode.AI_SERVICE_UNAVAILABLE, "down"));

        mvc.perform(get("/api/v1/interview/voice"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.provider").value(""))
                .andExpect(jsonPath("$.data.stt").value(false))
                .andExpect(jsonPath("$.data.tts").value(false));
    }

    @Test
    void anAnswerIsTranscribedForItsOwnerAndTheTranscriptCrosses() throws Exception {
        when(ai.transcribeAnswer(ALICE, "AAAA", "audio/webm", "zh"))
                .thenReturn(Map.of("text", "I led the ledger migration.",
                        "provider", "mock"));

        mvc.perform(post("/api/v1/interview/sessions/" + SESSION + "/voice/transcribe")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"audio\":\"AAAA\",\"mime\":\"audio/webm\",\"locale\":\"zh\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.text").value("I led the ledger migration."))
                .andExpect(jsonPath("$.data.provider").value("mock"));

        verify(interviews).requireReadOnly(ALICE, SESSION);
        verify(ai).transcribeAnswer(ALICE, "AAAA", "audio/webm", "zh");
    }

    @Test
    void anotherUsersSessionIsRefusedBeforeTheSpeechBudgetIsSpent() throws Exception {
        when(interviews.requireReadOnly(ALICE, SESSION)).thenThrow(
                new ApiException(ApiErrorCode.SESSION_NOT_FOUND, "Interview session not found"));

        mvc.perform(post("/api/v1/interview/sessions/" + SESSION + "/voice/transcribe")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"audio\":\"AAAA\"}"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error.code").value("SESSION_NOT_FOUND"));

        verify(ai, never()).transcribeAnswer(any(), any(), any(), any());
    }

    @Test
    void aBlankRecordingIsRefusedWithAFieldDetail() throws Exception {
        mvc.perform(post("/api/v1/interview/sessions/" + SESSION + "/voice/transcribe")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"audio\":\"  \"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("VALIDATION_FAILED"))
                .andExpect(jsonPath("$.error.details[0].field").value("audio"));

        verifyNoInteractions(ai);
    }

    @Test
    void aProviderThatHeardNothingIsAnEmptyAnswerNotASuccess() throws Exception {
        // An empty transcript would land in the answer box as a blank the
        // candidate cannot explain; saying the provider heard nothing is the
        // honest answer, and the page can prompt for a retry.
        when(ai.transcribeAnswer(ALICE, "AAAA", null, null))
                .thenReturn(Map.of("text", "   ", "provider", "mock"));

        mvc.perform(post("/api/v1/interview/sessions/" + SESSION + "/voice/transcribe")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"audio\":\"AAAA\"}"))
                .andExpect(status().isBadGateway())
                .andExpect(jsonPath("$.error.code").value("AI_SERVICE_EMPTY_RESPONSE"))
                .andExpect(jsonPath("$.error.message")
                        .value("The speech provider heard nothing"));
    }

    @Test
    void aQuestionIsSpokenBackAsTheClipTheProviderMade() throws Exception {
        when(ai.speakQuestion(ALICE, "Tell me about a hard migration.", "en"))
                .thenReturn(Map.of("audio", "UklGRg==", "mime", "audio/wav",
                        "provider", "mock"));

        mvc.perform(post("/api/v1/interview/sessions/" + SESSION + "/voice/speak")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"text\":\"Tell me about a hard migration.\",\"locale\":\"en\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.audio").value("UklGRg=="))
                .andExpect(jsonPath("$.data.mime").value("audio/wav"))
                .andExpect(jsonPath("$.data.provider").value("mock"));

        verify(ai).speakQuestion(ALICE, "Tell me about a hard migration.", "en");
    }

    @Test
    void aBlankLineIsNotSentToBeSpoken() throws Exception {
        mvc.perform(post("/api/v1/interview/sessions/" + SESSION + "/voice/speak")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"text\":\"\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("VALIDATION_FAILED"))
                .andExpect(jsonPath("$.error.details[0].field").value("text"));

        verifyNoInteractions(ai);
    }

    @Test
    void aProviderThatAnsweredNoAudioIsAnEmptyAnswerNotASilentSuccess() throws Exception {
        when(ai.speakQuestion(ALICE, "Question?", null))
                .thenReturn(Map.of("audio", "", "mime", "audio/wav"));

        mvc.perform(post("/api/v1/interview/sessions/" + SESSION + "/voice/speak")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"text\":\"Question?\"}"))
                .andExpect(status().isBadGateway())
                .andExpect(jsonPath("$.error.code").value("AI_SERVICE_EMPTY_RESPONSE"))
                .andExpect(jsonPath("$.error.message")
                        .value("The speech provider answered no audio"));
    }
}
