package com.careeros.activity.web;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.careeros.activity.entity.AgentRun;
import com.careeros.activity.entity.AgentTrace;
import com.careeros.activity.repository.AgentRunRepository;
import com.careeros.activity.repository.AgentTraceRepository;
import com.careeros.activity.repository.AiUsageEventRepository;
import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUserArgumentResolver;
import com.careeros.common.EnvelopeAdvice;
import com.careeros.common.GlobalExceptionHandler;
import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

/**
 * The observability surface: the agent-run feed, one run's traces, and the AI usage summary.
 * PagingApiIT pins the feed's paging contract; nothing stated the aggregates
 * (/ai-usage/summary) — six sums, a per-model breakdown and a status histogram built by
 * hand from two grouped queries — nor the 404 scoping on the run detail route.
 *
 * The aggregate worth the most here is `totalTokens`. It excludes `cachedTokens` even
 * though the field is right there in the same row, which looks like an omission until you
 * read the producer: ai-service's Anthropic adapter reports
 * `input_tokens = new + cache_read + cache_write` with `cached_tokens = cache_read`
 * (app/providers/llm/anthropic.py:28-30), so cached is a SUBSET of input — adding it to
 * the total would charge the same tokens twice. That cross-service arithmetic is pinned
 * below as the contract it is.
 */
class ActivityControllerTest {

    private static final UUID ALICE = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final UUID RUN = UUID.fromString("33333333-3333-4333-8333-333333333333");

    private AgentRunRepository runs;
    private AgentTraceRepository traces;
    private AiUsageEventRepository usage;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        runs = mock(AgentRunRepository.class);
        traces = mock(AgentTraceRepository.class);
        usage = mock(AiUsageEventRepository.class);
        mvc = MockMvcBuilders.standaloneSetup(
                        new ActivityController(runs, traces, usage))
                .setControllerAdvice(new EnvelopeAdvice(), new GlobalExceptionHandler())
                .setCustomArgumentResolvers(new CurrentUserArgumentResolver())
                .build();
        as(ALICE);
    }

    @AfterEach
    void clearPrincipal() {
        SecurityContextHolder.clearContext();
    }

    private static void as(UUID id) {
        SecurityContextHolder.getContext().setAuthentication(new UsernamePasswordAuthenticationToken(
                new AuthUser(id, "ada@example.invalid", "user"), null, List.of()));
    }

    private static void set(Object target, String field, Object value) {
        try {
            java.lang.reflect.Field f = target.getClass().getDeclaredField(field);
            f.setAccessible(true);
            f.set(target, value);
        } catch (ReflectiveOperationException e) {
            throw new IllegalStateException("cannot set " + field, e);
        }
    }

    private static AgentRun run(String agent, String status) {
        // AgentRun has no setters either (Hibernate writes it): the entity is filled
        // reflectively, the way the persistence layer fills it in production.
        // The int primitives take Integer through Field.set's unboxing.
        AgentRun r = new AgentRun();
        set(r, "id", RUN);
        set(r, "userId", ALICE);
        set(r, "agent", agent);
        set(r, "trigger", "chat");
        set(r, "status", status);
        set(r, "model", "claude-sonnet-4");
        set(r, "inputTokens", 1000);
        set(r, "outputTokens", 200);
        set(r, "cachedTokens", 800);
        set(r, "costUsd", new BigDecimal("0.0125"));
        set(r, "latencyMs", 1500);
        return r;
    }

    /** One row of the {@code usageByModel} projection: model, in, out, cached, cost, requests. */
    private static Object[] usageRow(String model, long in, long out, long cached,
                                     BigDecimal cost, long requests) {
        return new Object[] {model, in, out, cached, cost, requests};
    }

    private static AgentTrace trace(int seq, String kind, String agent,
                                    java.util.Map<String, Object> payload) {
        AgentTrace t = new AgentTrace();
        set(t, "id", 1L);
        set(t, "runId", RUN);
        set(t, "seq", seq);
        set(t, "kind", kind);
        set(t, "agent", agent);
        set(t, "payload", payload);
        return t;
    }

    // ------------------------------------------------------------ the aggregate

    @Test
    void total_tokens_excludes_cached_because_cached_is_a_subset_of_input() throws Exception {
        // The arithmetic the Anthropic adapter's Usage docstring locks on the Python side
        // (input_tokens = new + cache_read + cache_write; cached_tokens = cache_read),
        // restated on the Java side that renders it. One row: 1000 in, 200 out, 800 of the
        // input cached. Total is 1200, not 2000 — counting cached twice would invoice the
        // same cache reads at full price.
        when(usage.usageByModel(ALICE)).thenReturn(List.<Object[]>of(usageRow(
                "claude-sonnet-4", 1000, 200, 800, new BigDecimal("0.0125"), 3)));
        when(runs.statusCounts(ALICE)).thenReturn(List.<Object[]>of());

        mvc.perform(get("/api/v1/ai-usage/summary"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.inputTokens").value(1000))
                .andExpect(jsonPath("$.data.outputTokens").value(200))
                .andExpect(jsonPath("$.data.cachedTokens").value(800))
                .andExpect(jsonPath("$.data.totalTokens").value(1200))
                .andExpect(jsonPath("$.data.costUsd").value(0.0125))
                .andExpect(jsonPath("$.data.requests").value(3))
                .andExpect(jsonPath("$.data.perModel.claude-sonnet-4.cachedTokens").value(800))
                .andExpect(jsonPath("$.data.perModel.claude-sonnet-4.requests").value(3));
    }

    @Test
    void per_model_rows_sum_into_the_totals_and_a_missing_cost_is_zero_not_a_null() throws Exception {
        // Two models, one with a null SUM (PostgreSQL returns null for SUM over an empty
        // group — possible when usage rows exist with cost_usd unset). The controller
        // substitutes ZERO so the summary's cost is a number the page can add up.
        when(usage.usageByModel(ALICE)).thenReturn(List.<Object[]>of(
                usageRow("claude-sonnet-4", 1000, 200, 800, new BigDecimal("0.0125"), 3),
                usageRow("text-embed-3", 400, 0, 0, null, 40)));
        when(runs.statusCounts(ALICE)).thenReturn(List.<Object[]>of(
                new Object[] {"ok", 5L}, new Object[] {"failed", 1L}));

        mvc.perform(get("/api/v1/ai-usage/summary"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.inputTokens").value(1400))
                .andExpect(jsonPath("$.data.outputTokens").value(200))
                .andExpect(jsonPath("$.data.totalTokens").value(1600))
                .andExpect(jsonPath("$.data.costUsd").value(0.0125))
                .andExpect(jsonPath("$.data.requests").value(43))
                .andExpect(jsonPath("$.data.perModel.text-embed-3.costUsd").value(0))
                .andExpect(jsonPath("$.data.perModel.text-embed-3.cachedTokens").value(0))
                .andExpect(jsonPath("$.data.runsByStatus.ok").value(5))
                .andExpect(jsonPath("$.data.runsByStatus.failed").value(1));
    }

    @Test
    void an_account_with_no_usage_answers_zeros_not_an_error() throws Exception {
        // Both grouped queries come back empty: the honest answer is a zeroed summary the
        // dashboard can render, not a 500 from an empty row stream.
        when(usage.usageByModel(ALICE)).thenReturn(List.<Object[]>of());
        when(runs.statusCounts(ALICE)).thenReturn(List.<Object[]>of());

        mvc.perform(get("/api/v1/ai-usage/summary"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.inputTokens").value(0))
                .andExpect(jsonPath("$.data.outputTokens").value(0))
                .andExpect(jsonPath("$.data.cachedTokens").value(0))
                .andExpect(jsonPath("$.data.totalTokens").value(0))
                .andExpect(jsonPath("$.data.costUsd").value(0))
                .andExpect(jsonPath("$.data.requests").value(0))
                .andExpect(jsonPath("$.data.perModel").isEmpty())
                .andExpect(jsonPath("$.data.runsByStatus").isEmpty());
    }

    // ------------------------------------------------------------ the run detail route

    @Test
    void a_run_detail_answers_the_run_with_its_traces_in_order() throws Exception {
        when(runs.findByIdAndUserId(RUN, ALICE)).thenReturn(Optional.of(run("interview", "ok")));
        // AgentTrace has no setters at all (Hibernate writes it): the whole entity is built
        // through reflection, exactly the way the persistence layer fills it in production.
        AgentTrace t1 = trace(1, "prompt", "interview",
                java.util.Map.of("text", "tell me about kafka"));
        AgentTrace t2 = trace(2, "tool", "interview", java.util.Map.of("tool", "rag:search"));
        when(traces.findByRunIdOrderBySeqAsc(RUN)).thenReturn(List.of(t1, t2));

        mvc.perform(get("/api/v1/activity/runs/" + RUN))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.run.id").value(RUN.toString()))
                .andExpect(jsonPath("$.data.run.agent").value("interview"))
                .andExpect(jsonPath("$.data.run.model").value("claude-sonnet-4"))
                .andExpect(jsonPath("$.data.run.inputTokens").value(1000))
                .andExpect(jsonPath("$.data.run.costUsd").value(0.0125))
                .andExpect(jsonPath("$.data.traces[0].seq").value(1))
                .andExpect(jsonPath("$.data.traces[0].kind").value("prompt"))
                .andExpect(jsonPath("$.data.traces[0].payload.text").value("tell me about kafka"))
                .andExpect(jsonPath("$.data.traces[1].seq").value(2))
                .andExpect(jsonPath("$.data.traces[1].payload.tool").value("rag:search"));
    }

    @Test
    void a_foreign_or_unknown_run_is_404_and_no_trace_is_read() throws Exception {
        when(runs.findByIdAndUserId(RUN, ALICE)).thenReturn(Optional.empty());

        mvc.perform(get("/api/v1/activity/runs/" + RUN))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error.code").value("RUN_NOT_FOUND"))
                .andExpect(jsonPath("$.error.message").value("Agent run not found"));

        // The trace lookup is gated behind the run's ownership check: an unknown id must not
        // read (or count) another account's trace rows.
        verify(traces, never()).findByRunIdOrderBySeqAsc(any());
    }

    // ------------------------------------------------------------ the feed

    @Test
    void the_feed_answers_a_page_of_runs_and_the_agent_filter_reaches_the_query() throws Exception {
        AgentRun first = run("copilot", "ok");
        Page<AgentRun> page = new PageImpl<>(List.of(first), PageRequest.of(0, 30), 1);
        when(runs.findRecent(eq(ALICE), eq("copilot"), any())).thenReturn(page);

        mvc.perform(get("/api/v1/activity/runs").param("agent", "copilot"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.items[0].agent").value("copilot"))
                .andExpect(jsonPath("$.data.total").value(1));

        verify(runs).findRecent(ALICE, "copilot", org.springframework.data.domain.PageRequest.of(0, 30));
    }

    @Test
    void no_agent_filter_asks_the_query_for_null_and_the_principals_scope_is_used() throws Exception {
        when(runs.findRecent(eq(ALICE), any(), any())).thenReturn(
                new PageImpl<>(List.of(run("copilot", "ok")), PageRequest.of(0, 30), 1));

        mvc.perform(get("/api/v1/activity/runs"))
                .andExpect(status().isOk());

        verify(runs).findRecent(ALICE, null, org.springframework.data.domain.PageRequest.of(0, 30));
    }

    @Test
    void an_unauthenticated_caller_is_refused_before_any_aggregate_runs() throws Exception {
        SecurityContextHolder.clearContext();

        mvc.perform(get("/api/v1/ai-usage/summary")).andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.error.code").value("UNAUTHORIZED"));
        mvc.perform(get("/api/v1/activity/runs")).andExpect(status().isUnauthorized());
        mvc.perform(get("/api/v1/activity/runs/" + RUN)).andExpect(status().isUnauthorized());

        verify(runs, never()).statusCounts(any());
        verify(usage, never()).usageByModel(any());
    }
}
