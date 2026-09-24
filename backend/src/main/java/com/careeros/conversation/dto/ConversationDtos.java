package com.careeros.conversation.dto;

import com.fasterxml.jackson.annotation.JsonAlias;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;

public final class ConversationDtos {

    private ConversationDtos() {
    }

    /**
     * `lastMessagePreview` and `messageCount` are aggregates over `messages`, filled only where
     * the caller asked for a page: a single-row read has not looked at the thread, so both stay
     * null rather than claiming an empty chat.
     */
    public record ConversationItem(UUID id, String title, Map<String, Object> context,
                                   OffsetDateTime createdAt, OffsetDateTime updatedAt,
                                   String lastMessagePreview, Integer messageCount) {
    }

    public record MessageItem(UUID id, String role, String content, List<Object> artifacts,
                              List<Object> sources, List<Object> actions, UUID agentRunId,
                              OffsetDateTime createdAt) {
    }

    public record CreateConversationRequest(@Size(max = 200) String title, Map<String, Object> context) {
    }

    public record UpdateConversationRequest(@Size(max = 200) String title, Map<String, Object> context) {
    }

    public record ChatRequest(@JsonAlias("conversation_id") UUID conversationId,
                              @NotBlank @Size(max = 8000) String message,
                              Map<String, Object> context) {
    }

    public record ChatResponse(UUID conversationId, UUID userMessageId, UUID assistantMessageId,
                               String answer, List<Object> artifacts, List<Object> sources,
                               List<Object> actions, UUID runId) {
    }
}
