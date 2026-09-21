package com.careeros.conversation.web;

import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import com.careeros.common.PageDTO;
import com.careeros.conversation.dto.ConversationDtos.CreateConversationRequest;
import com.careeros.conversation.dto.ConversationDtos.ConversationItem;
import com.careeros.conversation.dto.ConversationDtos.MessageItem;
import com.careeros.conversation.dto.ConversationDtos.UpdateConversationRequest;
import com.careeros.conversation.service.ConversationService;
import jakarta.validation.Valid;
import java.util.List;
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
@RequestMapping("/api/v1/conversations")
public class ConversationController {

    private final ConversationService conversations;

    public ConversationController(ConversationService conversations) {
        this.conversations = conversations;
    }

    @GetMapping
    public PageDTO<ConversationItem> list(@CurrentUser AuthUser user,
                                          @RequestParam(defaultValue = "0") int page,
                                          @RequestParam(defaultValue = "20") int size) {
        return conversations.list(user.id(), page, Math.min(size, 100));
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ConversationItem create(@CurrentUser AuthUser user,
                                   @RequestBody(required = false) @Valid CreateConversationRequest request) {
        return conversations.create(user.id(), request == null
                ? new CreateConversationRequest(null, null) : request);
    }

    @GetMapping("/{id}")
    public ConversationItem get(@CurrentUser AuthUser user, @PathVariable UUID id) {
        return ConversationService.toItem(conversations.requireReadOnly(user.id(), id));
    }

    @PatchMapping("/{id}")
    public ConversationItem update(@CurrentUser AuthUser user, @PathVariable UUID id,
                                   @RequestBody @Valid UpdateConversationRequest request) {
        return conversations.update(user.id(), id, request);
    }

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void delete(@CurrentUser AuthUser user, @PathVariable UUID id) {
        conversations.delete(user.id(), id);
    }

    @GetMapping("/{id}/messages")
    public List<MessageItem> messages(@CurrentUser AuthUser user, @PathVariable UUID id) {
        return conversations.history(user.id(), id);
    }
}
