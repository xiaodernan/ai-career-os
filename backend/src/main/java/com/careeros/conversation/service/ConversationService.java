package com.careeros.conversation.service;

import com.careeros.ai.AiServiceClient;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.common.Json;
import com.careeros.common.PageDTO;
import com.careeros.conversation.dto.ConversationDtos.ChatResponse;
import com.careeros.conversation.dto.ConversationDtos.CreateConversationRequest;
import com.careeros.conversation.dto.ConversationDtos.ConversationItem;
import com.careeros.conversation.dto.ConversationDtos.MessageItem;
import com.careeros.conversation.dto.ConversationDtos.UpdateConversationRequest;
import com.careeros.conversation.entity.Conversation;
import com.careeros.conversation.entity.Message;
import com.careeros.conversation.repository.ConversationRepository;
import com.careeros.conversation.repository.MessageRepository;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Copilot conversations. v1 chat is the synchronous ai-service route; both messages persist here. */
@Service
public class ConversationService {

    private static final int HISTORY_TURNS = 12;

    private final ConversationRepository conversations;
    private final MessageRepository messages;
    private final AiServiceClient ai;

    public ConversationService(ConversationRepository conversations, MessageRepository messages,
                               AiServiceClient ai) {
        this.conversations = conversations;
        this.messages = messages;
        this.ai = ai;
    }

    @Transactional(readOnly = true)
    public PageDTO<ConversationItem> list(UUID userId, int page, int size) {
        var result = conversations.findByUserIdOrderByUpdatedAtDesc(userId, PageRequest.of(page, size));
        return PageDTO.from(result, ConversationService::toItem);
    }

    @Transactional
    public ConversationItem create(UUID userId, CreateConversationRequest request) {
        Conversation c = new Conversation();
        c.setUserId(userId);
        if (request.title() != null && !request.title().isBlank()) {
            c.setTitle(request.title().trim());
        }
        if (request.context() != null) {
            c.setContext(request.context());
        }
        conversations.save(c);
        return toItem(c);
    }

    @Transactional
    public ConversationItem update(UUID userId, UUID id, UpdateConversationRequest request) {
        Conversation c = require(userId, id);
        if (request.title() != null && !request.title().isBlank()) {
            c.setTitle(request.title().trim());
        }
        if (request.context() != null) {
            c.setContext(request.context());
        }
        return toItem(conversations.save(c));
    }

    @Transactional
    public void delete(UUID userId, UUID id) {
        conversations.delete(require(userId, id));
    }

    @Transactional(readOnly = true)
    public List<MessageItem> history(UUID userId, UUID conversationId) {
        requireReadOnly(userId, conversationId);
        return messages.findByConversationIdOrderByCreatedAtAsc(conversationId).stream()
                .map(ConversationService::toMessageItem).toList();
    }

    public ChatResponse chat(UUID userId, UUID conversationId, String message, Map<String, Object> context) {
        Conversation conversation = conversationId == null
                ? createForUser(userId, preview(message))
                : requireReadOnly(userId, conversationId);
        List<Map<String, Object>> history = historyPayload(conversation.getId());
        Map<String, Object> result = ai.copilotChatSync(message, history, conversation.getId(), context, userId);

        return persistTurn(conversation.getId(), userId, message, result);
    }

    private Conversation createForUser(UUID userId, String title) {
        Conversation c = new Conversation();
        c.setUserId(userId);
        c.setTitle(title);
        return conversations.save(c);
    }

    @Transactional
    public ChatResponse persistTurn(UUID conversationId, UUID userId, String userMessage,
                                    Map<String, Object> result) {
        Message user = new Message();
        user.setConversationId(conversationId);
        user.setUserId(userId);
        user.setRole("user");
        user.setContent(userMessage);
        messages.save(user);

        Message assistant = new Message();
        assistant.setConversationId(conversationId);
        assistant.setUserId(userId);
        assistant.setRole("assistant");
        assistant.setContent(Json.strOr(result, "answer", ""));
        assistant.setArtifacts(Json.arr(result.get("artifacts")));
        assistant.setSources(Json.arr(result.get("sources")));
        assistant.setActions(Json.arr(result.get("actions")));
        assistant.setAgentRunId(Json.uuidOrNull(result, "run_id"));
        messages.save(assistant);

        conversations.findById(conversationId).ifPresent(c -> {
            if ("New chat".equals(c.getTitle())) {
                c.setTitle(preview(userMessage));
            }
            conversations.save(c);
        });

        return new ChatResponse(conversationId, user.getId(), assistant.getId(),
                assistant.getContent(), assistant.getArtifacts(), assistant.getSources(),
                assistant.getActions(), assistant.getAgentRunId());
    }

    public Conversation requireReadOnly(UUID userId, UUID conversationId) {
        return conversations.findByIdAndUserId(conversationId, userId)
                .orElseThrow(() -> new ApiException(ApiErrorCode.CONVERSATION_NOT_FOUND,
                        "Conversation not found"));
    }

    @Transactional
    public Conversation require(UUID userId, UUID conversationId) {
        return requireReadOnly(userId, conversationId);
    }

    private List<Map<String, Object>> historyPayload(UUID conversationId) {
        List<Message> recent = messages.findByConversationIdOrderByCreatedAtDesc(conversationId,
                PageRequest.of(0, HISTORY_TURNS));
        List<Map<String, Object>> history = new ArrayList<>();
        for (int i = recent.size() - 1; i >= 0; i--) {
            Message m = recent.get(i);
            Map<String, Object> entry = new HashMap<>();
            entry.put("role", m.getRole());
            entry.put("content", m.getContent());
            history.add(entry);
        }
        return history;
    }

    private static String preview(String message) {
        if (message == null || message.isBlank()) {
            return "New chat";
        }
        String t = message.trim();
        return t.length() <= 60 ? t : t.substring(0, 60) + "…";
    }

    public static ConversationItem toItem(Conversation c) {
        return new ConversationItem(c.getId(), c.getTitle(), c.getContext(), c.getCreatedAt(),
                c.getUpdatedAt());
    }

    static MessageItem toMessageItem(Message m) {
        return new MessageItem(m.getId(), m.getRole(), m.getContent(), m.getArtifacts(),
                m.getSources(), m.getActions(), m.getAgentRunId(), m.getCreatedAt());
    }
}
