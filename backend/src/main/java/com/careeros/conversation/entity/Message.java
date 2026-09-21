package com.careeros.conversation.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.annotations.UuidGenerator;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "messages")
public class Message {

    @Id
    @UuidGenerator
    @Column(name = "id", nullable = false, updatable = false)
    private UUID id;

    @Column(name = "conversation_id", nullable = false, updatable = false)
    private UUID conversationId;

    @Column(name = "user_id", nullable = false, updatable = false)
    private UUID userId;

    @Column(name = "role", nullable = false)
    private String role;

    @Column(name = "content", nullable = false)
    private String content = "";

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "artifacts", nullable = false)
    private List<Object> artifacts = List.of();

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "sources", nullable = false)
    private List<Object> sources = List.of();

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "actions", nullable = false)
    private List<Object> actions = List.of();

    @Column(name = "agent_run_id")
    private UUID agentRunId;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private OffsetDateTime createdAt;

    public UUID getId() {
        return id;
    }

    public UUID getConversationId() {
        return conversationId;
    }

    public void setConversationId(UUID conversationId) {
        this.conversationId = conversationId;
    }

    public UUID getUserId() {
        return userId;
    }

    public void setUserId(UUID userId) {
        this.userId = userId;
    }

    public String getRole() {
        return role;
    }

    public void setRole(String role) {
        this.role = role;
    }

    public String getContent() {
        return content;
    }

    public void setContent(String content) {
        this.content = content == null ? "" : content;
    }

    public List<Object> getArtifacts() {
        return artifacts;
    }

    public void setArtifacts(List<Object> artifacts) {
        this.artifacts = artifacts == null ? List.of() : artifacts;
    }

    public List<Object> getSources() {
        return sources;
    }

    public void setSources(List<Object> sources) {
        this.sources = sources == null ? List.of() : sources;
    }

    public List<Object> getActions() {
        return actions;
    }

    public void setActions(List<Object> actions) {
        this.actions = actions == null ? List.of() : actions;
    }

    public UUID getAgentRunId() {
        return agentRunId;
    }

    public void setAgentRunId(UUID agentRunId) {
        this.agentRunId = agentRunId;
    }

    public OffsetDateTime getCreatedAt() {
        return createdAt;
    }
}
