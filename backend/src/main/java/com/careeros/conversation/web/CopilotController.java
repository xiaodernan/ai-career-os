package com.careeros.conversation.web;

import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import com.careeros.conversation.dto.ConversationDtos.ChatRequest;
import com.careeros.conversation.dto.ConversationDtos.ChatResponse;
import com.careeros.conversation.service.ConversationService;
import com.careeros.conversation.service.CopilotStreamService;
import jakarta.validation.Valid;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

/**
 * Two ways to ask the copilot one question. {@code /chat} blocks and answers with the stored
 * turn — the shape a script, the e2e suite and the eval harness want. {@code /chat/stream} is
 * what the copilot page uses: an event stream of the turn as it happens, closing with the same
 * {@link ChatResponse} once both messages are stored.
 */
@RestController
@RequestMapping("/api/v1/copilot")
public class CopilotController {

    private final ConversationService conversations;
    private final CopilotStreamService streams;

    public CopilotController(ConversationService conversations, CopilotStreamService streams) {
        this.conversations = conversations;
        this.streams = streams;
    }

    @PostMapping("/chat")
    public ChatResponse chat(@CurrentUser AuthUser user, @RequestBody @Valid ChatRequest request) {
        return conversations.chat(user.id(), request.conversationId(), request.message(),
                request.context());
    }

    @PostMapping(value = "/chat/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter chatStream(@CurrentUser AuthUser user, @RequestBody @Valid ChatRequest request) {
        return streams.stream(user.id(), request.conversationId(), request.message(),
                request.context());
    }
}
