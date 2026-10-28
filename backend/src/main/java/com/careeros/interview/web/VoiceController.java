package com.careeros.interview.web;

import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import com.careeros.interview.dto.InterviewDtos.VoiceAnswerRequest;
import com.careeros.interview.dto.InterviewDtos.VoiceClip;
import com.careeros.interview.dto.InterviewDtos.VoiceLineRequest;
import com.careeros.interview.dto.InterviewDtos.VoiceState;
import com.careeros.interview.dto.InterviewDtos.VoiceTranscript;
import com.careeros.interview.service.VoiceService;
import jakarta.validation.Valid;
import java.util.UUID;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

/**
 * The interview's microphone and speaker (19.6). The state route is read before
 * a session exists -- the page decides which speech path it has before the
 * first question -- while listening and speaking are scoped to one of the
 * caller's own sessions.
 */
@RestController
public class VoiceController {

    private final VoiceService voice;

    public VoiceController(VoiceService voice) {
        this.voice = voice;
    }

    @GetMapping("/api/v1/interview/voice")
    public VoiceState state(@CurrentUser AuthUser user) {
        return voice.state(user.id());
    }

    @PostMapping("/api/v1/interview/sessions/{id}/voice/transcribe")
    public VoiceTranscript transcribe(@CurrentUser AuthUser user, @PathVariable UUID id,
                                      @RequestBody @Valid VoiceAnswerRequest request) {
        return voice.transcribe(user.id(), id, request);
    }

    @PostMapping("/api/v1/interview/sessions/{id}/voice/speak")
    public VoiceClip speak(@CurrentUser AuthUser user, @PathVariable UUID id,
                           @RequestBody @Valid VoiceLineRequest request) {
        return voice.speak(user.id(), id, request);
    }
}
