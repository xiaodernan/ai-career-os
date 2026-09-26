package com.careeros.conversation.service;

import com.careeros.ai.AiServiceClient;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.common.Json;
import com.careeros.common.PageDTO;
import com.careeros.common.Texts;
import com.careeros.common.Paging;
import com.careeros.conversation.dto.ConversationDtos.ChatResponse;
import com.careeros.conversation.dto.ConversationDtos.CreateConversationRequest;
import com.careeros.conversation.dto.ConversationDtos.ConversationItem;
import com.careeros.conversation.dto.ConversationDtos.MessageItem;
import com.careeros.conversation.dto.ConversationDtos.UpdateConversationRequest;
import com.careeros.conversation.entity.Conversation;
import com.careeros.conversation.entity.Message;
import com.careeros.conversation.repository.ConversationDigestRepository;
import com.careeros.conversation.repository.ConversationRepository;
import com.careeros.conversation.repository.MessageRepository;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Copilot conversations. Two routes reach the same turn: {@link #chat}, the blocking call, and
 * the streaming one ({@link CopilotStreamService}), which runs the turn on ai-service's task bus
 * and calls {@link #persistTurn} when it reports done. Both messages persist here either way —
 * the turn is stored by the server, never by whichever response the browser happened to keep.
 */
@Service
public class ConversationService {

    private static final int HISTORY_TURNS = 12;
    /** Code units a chat title or a sidebar preview is allowed to occupy. */
    private static final int PREVIEW_UNITS = 60;

    private final ConversationRepository conversations;
    private final MessageRepository messages;
    private final ConversationDigestRepository digests;
    private final AiServiceClient ai;

    public ConversationService(ConversationRepository conversations, MessageRepository messages,
                               ConversationDigestRepository digests, AiServiceClient ai) {
        this.conversations = conversations;
        this.messages = messages;
        this.digests = digests;
        this.ai = ai;
    }

    @Transactional(readOnly = true)
    public PageDTO<ConversationItem> list(UUID userId, int page, int size) {
        var result = conversations.findByUserIdOrderByUpdatedAtDesc(userId, Paging.of(page, size).pageable());
        Map<UUID, ConversationDigestRepository.Digest> rows = digests.forConversations(
                result.getContent().stream().map(Conversation::getId).toList());
        return PageDTO.from(result,
                c -> toItem(c, rows.getOrDefault(c.getId(), ConversationDigestRepository.Digest.UNKNOWN)));
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
        ChatTurn turn = beginTurn(userId, conversationId, message);
        Map<String, Object> result = ai.copilotChatSync(message, turn.history(), turn.conversationId(),
                context, userId);

        return persistTurn(turn.conversationId(), userId, message, result);
    }

    /**
     * The resolved start of a turn: which conversation it lands in (created here when the caller
     * has none) and the window the model is shown. The streaming route asks for this, runs the
     * turn elsewhere, and comes back for {@link #persistTurn} with the answer.
     */
    public record ChatTurn(UUID conversationId, List<Map<String, Object>> history) {
    }

    public ChatTurn beginTurn(UUID userId, UUID conversationId, String message) {
        Conversation conversation = conversationId == null
                ? createForUser(userId, preview(message))
                : requireReadOnly(userId, conversationId);
        return new ChatTurn(conversation.getId(), historyPayload(conversation.getId()));
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
                Paging.first(HISTORY_TURNS));
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

    static String preview(String message) {
        if (message == null || message.isBlank()) {
            return "New chat";
        }
        String t = message.trim();
        if (t.length() <= PREVIEW_UNITS) {
            return t;
        }
        return Texts.truncate(t, PREVIEW_UNITS) + "…";
    }

    static String excerpt(String content) {
        if (content == null || content.isBlank()) {
            return null;
        }
        // The sidebar renders one line, and an assistant answer is markdown: newlines would
        // render as gaps that look like missing data, so the preview is folded onto one line.
        String t = content.strip().replaceAll("\\s+", " ");
        return t.length() <= PREVIEW_UNITS ? t : Texts.truncate(t, PREVIEW_UNITS) + "…";
    }

    public static ConversationItem toItem(Conversation c) {
        return toItem(c, ConversationDigestRepository.Digest.UNKNOWN);
    }

    public static ConversationItem toItem(Conversation c, ConversationDigestRepository.Digest digest) {
        return new ConversationItem(c.getId(), c.getTitle(), c.getContext(), c.getCreatedAt(),
                c.getUpdatedAt(), excerpt(digest.lastMessage()), digest.messageCount());
    }

    static MessageItem toMessageItem(Message m) {
        return new MessageItem(m.getId(), m.getRole(), m.getContent(), m.getArtifacts(),
                m.getSources(), m.getActions(), m.getAgentRunId(), m.getCreatedAt());
    }
}
