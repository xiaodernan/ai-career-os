package com.careeros.ai.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.argThat;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.ai.AiServiceClient;
import com.careeros.ai.dto.GrowthReportRequest;
import com.careeros.ai.entity.GrowthPlan;
import com.careeros.ai.repository.GrowthPlanRepository;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

/**
 * 10.4's two rules, neither of which an integration test can pin cheaply:
 *
 * <p>One — the diff chain. A caller who brings no `previous` runs against the stored report's
 * gap block, so the second report for a role is a diff even when the browser holds nothing.
 * A caller who brings `previous` keeps it: the frontend's freshly-computed copy beats the
 * stored one, and the two must never be mixed into a body that carries both.
 *
 * <p>Two — the store is best-effort. The user is holding the report the moment the engine
 * answers; a failed insert must not turn a computed answer into a 500. The next run diffs
 * against nothing, which is a degraded memory, not a lost answer.
 */
class GrowthServiceTest {

    private static final UUID USER = UUID.randomUUID();
    private static final String ROLE = "Senior Backend Engineer";

    private AiServiceClient ai;
    private GrowthPlanRepository plans;
    private GrowthService service;

    @BeforeEach
    void setUp() {
        ai = mock(AiServiceClient.class);
        plans = mock(GrowthPlanRepository.class);
        service = new GrowthService(ai, plans);
        when(ai.growthReport(any(GrowthReportRequest.class), any()))
                .thenReturn(Map.of("gap", Map.of("coverage", 0.42)));
    }

    private GrowthReportRequest request(Map<String, Object> previous) {
        return new GrowthReportRequest(ROLE, null, null, null, "CNY", null, previous);
    }

    @Test
    void a_caller_without_previous_runs_against_the_stored_gap_block() {
        GrowthPlan stored = new GrowthPlan();
        stored.setReport(Map.of("gap", Map.of("coverage", 0.3, "gaps", java.util.List.of("Kubernetes"))));
        when(plans.findFirstByUserIdAndTargetRoleIgnoreCaseOrderByCreatedAtDesc(USER, ROLE))
                .thenReturn(Optional.of(stored));

        service.report(USER, request(null));

        verify(ai).growthReport(argThat(r -> r.previous()
                .equals(Map.of("coverage", 0.3, "gaps", java.util.List.of("Kubernetes")))), eq(USER));
    }

    @Test
    void a_caller_brought_previous_keeps_it_and_the_stored_row_is_never_read() {
        Map<String, Object> brought = Map.of("coverage", 0.5);

        service.report(USER, request(brought));

        verify(plans, never()).findFirstByUserIdAndTargetRoleIgnoreCaseOrderByCreatedAtDesc(any(), any());
        verify(ai).growthReport(argThat(r -> r.previous() == brought), any());
    }

    @Test
    void a_first_run_has_no_previous_and_still_stores_the_row() {
        when(plans.findFirstByUserIdAndTargetRoleIgnoreCaseOrderByCreatedAtDesc(USER, ROLE))
                .thenReturn(Optional.empty());

        Map<String, Object> out = service.report(USER, request(null));

        verify(ai).growthReport(argThat(r -> r.previous() == null), any());
        ArgumentCaptor<GrowthPlan> saved = ArgumentCaptor.forClass(GrowthPlan.class);
        verify(plans).save(saved.capture());
        assertThat(saved.getValue().getUserId()).isEqualTo(USER);
        assertThat(saved.getValue().getTargetRole()).isEqualTo(ROLE);
        assertThat(saved.getValue().getCoverage()).isEqualTo(0.42);
        assertThat(saved.getValue().getReport()).isEqualTo(out);
    }

    @Test
    void the_role_is_trimmed_before_the_lookup_and_the_store_agree_on_it() {
        when(plans.findFirstByUserIdAndTargetRoleIgnoreCaseOrderByCreatedAtDesc(USER, ROLE))
                .thenReturn(Optional.empty());

        service.report(USER, new GrowthReportRequest(ROLE + "  ", null, null, null, "CNY", null, null));

        verify(plans).findFirstByUserIdAndTargetRoleIgnoreCaseOrderByCreatedAtDesc(USER, ROLE);
        ArgumentCaptor<GrowthPlan> saved = ArgumentCaptor.forClass(GrowthPlan.class);
        verify(plans).save(saved.capture());
        assertThat(saved.getValue().getTargetRole()).isEqualTo(ROLE);
    }

    @Test
    void a_failed_store_returns_the_answer_instead_of_failing_the_call() {
        when(plans.findFirstByUserIdAndTargetRoleIgnoreCaseOrderByCreatedAtDesc(USER, ROLE))
                .thenReturn(Optional.empty());
        when(plans.save(any(GrowthPlan.class))).thenThrow(new RuntimeException("db gone"));

        Map<String, Object> out = service.report(USER, request(null));

        assertThat(out).isEqualTo(Map.of("gap", Map.of("coverage", 0.42)));
    }

    @Test
    void a_report_without_a_gap_block_stores_a_zero_coverage_row() {
        when(plans.findFirstByUserIdAndTargetRoleIgnoreCaseOrderByCreatedAtDesc(USER, ROLE))
                .thenReturn(Optional.empty());
        when(ai.growthReport(any(GrowthReportRequest.class), any()))
                .thenReturn(Map.of("readiness", Map.of("verdict", "not_ready")));

        service.report(USER, request(null));

        ArgumentCaptor<GrowthPlan> saved = ArgumentCaptor.forClass(GrowthPlan.class);
        verify(plans).save(saved.capture());
        assertThat(saved.getValue().getCoverage()).isZero();
    }
}
