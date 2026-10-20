package com.careeros.report.service;

import com.careeros.activity.entity.AgentRun;
import com.careeros.activity.repository.AgentRunRepository;
import com.careeros.ai.AiServiceClient;
import com.careeros.common.Paging;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Production monitoring (16.1): agent health, cost, and regression detection.
 *
 * <p>The health report is a pure function over the caller's agent runs, so the
 * backend's job is to hand it those rows. The engine never reads the observability
 * tables itself — the backend owns the domain writes, and a second reader of the
 * same table is a second answer to the same question.
 */
@Service
public class MonitoringService {

    /** The window the report covers; a cap keeps the request bounded. */
    private static final int MAX_RUNS = 500;

    private final AiServiceClient aiService;
    private final AgentRunRepository runs;

    public MonitoringService(AiServiceClient aiService, AgentRunRepository runs) {
        this.aiService = aiService;
        this.runs = runs;
    }

    /**
     * The health report for the dashboard. The ai-service computes error rate,
     * latency percentiles, cost/token totals, and regression verdicts; this
     * method supplies the rows and forwards the call.
     */
    @Transactional(readOnly = true)
    public Map<String, Object> healthReport(UUID userId) {
        List<Map<String, Object>> rows = runs.findRecent(userId, null, Paging.first(MAX_RUNS)).stream()
                .map(MonitoringService::toInput)
                .toList();
        return aiService.healthReport(userId, rows);
    }

    /**
     * One run as the engine reads it. The field names are the engine's own
     * (`latency_ms`, `input_tokens`, `output_tokens`, `cost_usd`); a field the
     * row does not carry is left out rather than sent as null, so the engine's
     * own "skip what you cannot parse" rule decides.
     */
    private static Map<String, Object> toInput(AgentRun r) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("id", r.getId().toString());
        row.put("status", r.getStatus());
        row.put("agent", r.getAgent());
        row.put("trigger", r.getTrigger());
        if (r.getModel() != null) {
            row.put("model", r.getModel());
        }
        row.put("input_tokens", r.getInputTokens());
        row.put("output_tokens", r.getOutputTokens());
        row.put("latency_ms", r.getLatencyMs());
        if (r.getCostUsd() != null) {
            row.put("cost_usd", r.getCostUsd());
        }
        if (r.getStartedAt() != null) {
            row.put("started_at", r.getStartedAt().toString());
        }
        if (r.getError() != null) {
            row.put("error", r.getError());
        }
        return row;
    }
}
