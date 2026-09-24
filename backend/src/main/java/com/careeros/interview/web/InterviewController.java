package com.careeros.interview.web;

import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import com.careeros.common.PageDTO;
import com.careeros.interview.dto.InterviewDtos.AnswerRequest;
import com.careeros.interview.dto.InterviewDtos.AnswerResponse;
import com.careeros.interview.dto.InterviewDtos.CreateSessionRequest;
import com.careeros.interview.dto.InterviewDtos.FinalizeResponse;
import com.careeros.interview.dto.InterviewDtos.OpeningResponse;
import com.careeros.interview.dto.InterviewDtos.SessionDetail;
import com.careeros.interview.dto.InterviewDtos.SessionItem;
import com.careeros.interview.service.InterviewService;
import jakarta.validation.Valid;
import java.util.Map;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/interview/sessions")
public class InterviewController {

    private final InterviewService interviews;

    public InterviewController(InterviewService interviews) {
        this.interviews = interviews;
    }

    @GetMapping
    public PageDTO<SessionItem> list(@CurrentUser AuthUser user,
                                     @RequestParam(defaultValue = "0") int page,
                                     @RequestParam(defaultValue = "20") int size) {
        return interviews.list(user.id(), page, size);
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public SessionItem create(@CurrentUser AuthUser user,
                              @RequestBody @Valid CreateSessionRequest request) {
        return interviews.create(user.id(), request);
    }

    @GetMapping("/{id}")
    public SessionDetail detail(@CurrentUser AuthUser user, @PathVariable UUID id) {
        return interviews.detail(user.id(), id);
    }

    @PatchMapping("/{id}")
    public SessionItem update(@CurrentUser AuthUser user, @PathVariable UUID id,
                              @RequestBody Map<String, Object> patch) {
        return interviews.update(user.id(), id, patch);
    }

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void delete(@CurrentUser AuthUser user, @PathVariable UUID id) {
        interviews.delete(user.id(), id);
    }

    @PostMapping("/{id}/opening")
    public OpeningResponse opening(@CurrentUser AuthUser user, @PathVariable UUID id) {
        return interviews.opening(user.id(), id);
    }

    @PostMapping("/{id}/answer")
    public AnswerResponse answer(@CurrentUser AuthUser user, @PathVariable UUID id,
                                 @RequestBody @Valid AnswerRequest request) {
        return interviews.answer(user.id(), id, request.answer());
    }

    @PostMapping("/{id}/finalize")
    public FinalizeResponse finalize(@CurrentUser AuthUser user, @PathVariable UUID id) {
        return interviews.finalize(user.id(), id);
    }
}
