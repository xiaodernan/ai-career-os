package com.careeros.interview.service;

import com.careeros.ai.AiServiceClient;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.interview.dto.InterviewDtos.VoiceAnswerRequest;
import com.careeros.interview.dto.InterviewDtos.VoiceClip;
import com.careeros.interview.dto.InterviewDtos.VoiceLineRequest;
import com.careeros.interview.dto.InterviewDtos.VoiceState;
import com.careeros.interview.dto.InterviewDtos.VoiceTranscript;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;

/**
 * The interview's voice seam (19.6): whether the deployment can hear and
 * speak, one answer transcribed, one question spoken.
 *
 * <p>The scoring path is untouched -- a transcript is text, and the text
 * interview evaluates it the same way however it was typed. That is also why
 * every call here is an enhancement: an ai-service that cannot answer leaves
 * the controls to the browser's own speech APIs rather than failing a page
 * that is otherwise running an interview.
 */
@Service
public class VoiceService {

    private final AiServiceClient ai;
    private final InterviewService interviews;

    public VoiceService(AiServiceClient ai, InterviewService interviews) {
        this.ai = ai;
        this.interviews = interviews;
    }

    /** Best-effort: "cannot ask" is the same answer as "no provider", which the page can live with. */
    public VoiceState state(UUID userId) {
        try {
            Map<String, Object> raw = ai.voiceState(userId);
            return new VoiceState(text(raw.get("provider")), truthy(raw.get("stt")),
                    truthy(raw.get("tts")));
        } catch (RuntimeException e) {
            return new VoiceState("", false, false);
        }
    }

    public VoiceTranscript transcribe(UUID userId, UUID sessionId, VoiceAnswerRequest request) {
        // Only the caller's own session: the route spends the deployment's speech
        // budget, so an id that is not theirs is a 404 before any spend.
        interviews.requireReadOnly(userId, sessionId);
        Map<String, Object> raw = ai.transcribeAnswer(userId, request.audio(), request.mime(),
                request.locale());
        String text = text(raw.get("text"));
        if (text == null) {
            throw new ApiException(ApiErrorCode.AI_SERVICE_EMPTY_RESPONSE,
                    "The speech provider heard nothing");
        }
        return new VoiceTranscript(text, text(raw.get("provider")));
    }

    public VoiceClip speak(UUID userId, UUID sessionId, VoiceLineRequest request) {
        interviews.requireReadOnly(userId, sessionId);
        Map<String, Object> raw = ai.speakQuestion(userId, request.text(), request.locale());
        String audio = text(raw.get("audio"));
        if (audio == null) {
            throw new ApiException(ApiErrorCode.AI_SERVICE_EMPTY_RESPONSE,
                    "The speech provider answered no audio");
        }
        return new VoiceClip(audio, text(raw.get("mime")), text(raw.get("provider")));
    }

    private static String text(Object value) {
        if (value instanceof String s) {
            String trimmed = s.strip();
            return trimmed.isEmpty() ? null : trimmed;
        }
        return null;
    }

    private static boolean truthy(Object value) {
        return Boolean.TRUE.equals(value) || "true".equals(value);
    }
}
