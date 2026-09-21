package com.careeros.conversation.web;

import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import com.careeros.conversation.dto.ConversationDtos.ChatRequest;
import com.careeros.conversation.dto.ConversationDtos.ChatResponse;
import com.careeros.conversation.service.ConversationService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/copilot")
public class CopilotController {

    private final ConversationService conversations;

    public CopilotController(ConversationService conversations) {
        this.conversations = conversations;
    }

    @PostMapping("/chat")
    public ChatResponse chat(@CurrentUser AuthUser user, @RequestBody @Valid ChatRequest request) {
        return conversations.chat(user.id(), request.conversationId(), request.message(),
                request.context());
    }
}
