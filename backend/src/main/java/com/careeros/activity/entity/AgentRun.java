package com.careeros.activity.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.UUID;

/** Rows are written by ai-service; the backend exposes read-only activity views. */
@Entity
@Table(name = "agent_runs")
public class AgentRun {

    @Id
    @Column(name = "id", nullable = false, updatable = false)
    private UUID id;

    @Column(name = "user_id", nullable = false, updatable = false)
    private UUID userId;

    @Column(name = "root_run_id")
    private UUID rootRunId;

    @Column(name = "conversation_id")
    private UUID conversationId;

    @Column(name = "agent", nullable = false)
    private String agent;

    @Column(name = "trigger", nullable = false)
    private String trigger;

    @Column(name = "status", nullable = false)
    private String status;

    @Column(name = "model")
    private String model;

    @Column(name = "input_tokens", nullable = false)
    private int inputTokens;

    @Column(name = "output_tokens", nullable = false)
    private int outputTokens;

    @Column(name = "cached_tokens", nullable = false)
    private int cachedTokens;

    @Column(name = "cost_usd", nullable = false, precision = 12, scale = 6)
    private BigDecimal costUsd;

    @Column(name = "latency_ms", nullable = false)
    private int latencyMs;

    @Column(name = "error")
    private String error;

    @Column(name = "started_at", nullable = false)
    private OffsetDateTime startedAt;

    @Column(name = "finished_at")
    private OffsetDateTime finishedAt;

    public UUID getId() {
        return id;
    }

    public UUID getUserId() {
        return userId;
    }

    public UUID getRootRunId() {
        return rootRunId;
    }

    public UUID getConversationId() {
        return conversationId;
    }

    public String getAgent() {
        return agent;
    }

    public String getTrigger() {
        return trigger;
    }

    public String getStatus() {
        return status;
    }

    public String getModel() {
        return model;
    }

    public int getInputTokens() {
        return inputTokens;
    }

    public int getOutputTokens() {
        return outputTokens;
    }

    public int getCachedTokens() {
        return cachedTokens;
    }

    public BigDecimal getCostUsd() {
        return costUsd;
    }

    public int getLatencyMs() {
        return latencyMs;
    }

    public String getError() {
        return error;
    }

    public OffsetDateTime getStartedAt() {
        return startedAt;
    }

    public OffsetDateTime getFinishedAt() {
        return finishedAt;
    }
}
