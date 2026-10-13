package com.careeros.activity.web;

import com.careeros.activity.entity.AgentRun;
import com.careeros.activity.entity.AgentTrace;
import com.careeros.activity.repository.AgentRunRepository;
import com.careeros.activity.repository.AgentTraceRepository;
import com.careeros.activity.repository.AiUsageEventRepository;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import com.careeros.common.PageDTO;
import com.careeros.common.Paging;
import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class ActivityController {

    public record RunItem(UUID id, String agent, String trigger, String status, String model,
                          int inputTokens, int outputTokens, int cachedTokens, BigDecimal costUsd,
                          int latencyMs, String error, OffsetDateTime startedAt,
                          OffsetDateTime finishedAt, UUID rootRunId, UUID conversationId) {
    }

    public record TraceItem(long seq, String kind, String agent, Map<String, Object> payload,
                            OffsetDateTime createdAt) {
    }

    public record RunDetail(RunItem run, List<TraceItem> traces) {
    }

    private final AgentRunRepository runs;
    private final AgentTraceRepository traces;
    private final AiUsageEventRepository usage;

    public ActivityController(AgentRunRepository runs, AgentTraceRepository traces,
                              AiUsageEventRepository usage) {
        this.runs = runs;
        this.traces = traces;
        this.usage = usage;
    }

    @GetMapping("/api/v1/activity/runs")
    @Transactional(readOnly = true)
    public PageDTO<RunItem> listRuns(@CurrentUser AuthUser user,
                                      @RequestParam(defaultValue = "0") int page,
                                      @RequestParam(defaultValue = "30") int size,
                                      @RequestParam(required = false) String agent) {
        return PageDTO.from(runs.findRecent(user.id(), agent, Paging.of(page, size).pageable()),
                ActivityController::toItem);
    }

    @GetMapping("/api/v1/activity/runs/{id}")
    @Transactional(readOnly = true)
    public RunDetail runDetail(@CurrentUser AuthUser user, @PathVariable UUID id) {
        AgentRun run = runs.findByIdAndUserId(id, user.id())
                .orElseThrow(() -> new ApiException(ApiErrorCode.RUN_NOT_FOUND, "Agent run not found"));
        List<TraceItem> traceItems = traces.findByRunIdOrderBySeqAsc(id).stream()
                .map(t -> new TraceItem(t.getSeq(), t.getKind(), t.getAgent(), t.getPayload(),
                        t.getCreatedAt()))
                .toList();
        return new RunDetail(toItem(run), traceItems);
    }

    @GetMapping("/api/v1/ai-usage/summary")
    @Transactional(readOnly = true)
    public Map<String, Object> usageSummary(@CurrentUser AuthUser user) {
        long inTokens = 0;
        long outTokens = 0;
        long cachedTokens = 0;
        BigDecimal cost = BigDecimal.ZERO;
        long requests = 0;
        Map<String, Object> perModel = new LinkedHashMap<>();
        for (Object[] row : usage.usageByModel(user.id())) {
            String model = (String) row[0];
            long in = num(row[1]);
            long out = num(row[2]);
            long cached = num(row[3]);
            BigDecimal modelCost = row[4] == null ? BigDecimal.ZERO : (BigDecimal) row[4];
            long count = num(row[5]);
            inTokens += in;
            outTokens += out;
            cachedTokens += cached;
            cost = cost.add(modelCost);
            requests += count;
            perModel.put(model, Map.of("inputTokens", in, "outputTokens", out,
                    "cachedTokens", cached, "costUsd", modelCost, "requests", count));
        }
        Map<String, Long> runStatuses = new LinkedHashMap<>();
        for (Object[] row : runs.statusCounts(user.id())) {
            runStatuses.put((String) row[0], num(row[1]));
        }
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("inputTokens", inTokens);
        result.put("outputTokens", outTokens);
        result.put("cachedTokens", cachedTokens);
        result.put("totalTokens", inTokens + outTokens);
        result.put("costUsd", cost);
        result.put("requests", requests);
        result.put("perModel", perModel);
        result.put("runsByStatus", runStatuses);
        return result;
    }

    private static long num(Object v) {
        return v == null ? 0 : ((Number) v).longValue();
    }

    private static RunItem toItem(AgentRun r) {
        return new RunItem(r.getId(), r.getAgent(), r.getTrigger(), r.getStatus(), r.getModel(),
                r.getInputTokens(), r.getOutputTokens(), r.getCachedTokens(), r.getCostUsd(),
                r.getLatencyMs(), r.getError(), r.getStartedAt(), r.getFinishedAt(),
                r.getRootRunId(), r.getConversationId());
    }
}
