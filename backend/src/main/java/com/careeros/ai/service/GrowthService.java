package com.careeros.ai.service;

import com.careeros.ai.AiServiceClient;
import com.careeros.ai.dto.GrowthReportRequest;
import com.careeros.ai.entity.GrowthPlan;
import com.careeros.ai.repository.GrowthPlanRepository;
import java.util.Map;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

/**
 * The growth report's one write path (roadmap 10.4): every run is stored, and the next
 * run for the same (user, role) diffs against the stored one unless the caller brought
 * its own `previous`.
 *
 * <p>The AI call deliberately sits outside any transaction — a report that composes five
 * engines can take seconds, and holding a DB connection across it buys nothing. What is
 * transactional is the single save at the end; a failure there fails the response rather
 * than returning a report the caller will believe was kept.
 *
 * <p>The `previous` handed to the engine is the stored report's *gap block*, not the whole
 * report: that is the shape `diff_progress` reads (coverage plus the per-skill states),
 * and it is also what the frontend hands back today, so both callers speak one shape.
 */
@Service
public class GrowthService {

    private static final Logger log = LoggerFactory.getLogger(GrowthService.class);

    private final AiServiceClient ai;
    private final GrowthPlanRepository plans;

    public GrowthService(AiServiceClient ai, GrowthPlanRepository plans) {
        this.ai = ai;
        this.plans = plans;
    }

    public Map<String, Object> report(UUID userId, GrowthReportRequest request) {
        String role = request.targetRole().trim();
        Map<String, Object> previous = request.previous() != null
                ? request.previous()
                : storedGapBlock(userId, role);
        Map<String, Object> report = ai.growthReport(withPrevious(request, previous), userId);
        store(userId, role, report);
        return report;
    }

    /** The stored run's gap block, or null when this is the role's first report here. */
    private Map<String, Object> storedGapBlock(UUID userId, String role) {
        return plans.findFirstByUserIdAndTargetRoleIgnoreCaseOrderByCreatedAtDesc(userId, role)
                .map(GrowthPlan::getReport)
                .map(r -> (Map<String, Object>) r.get("gap"))
                .orElse(null);
    }

    private static GrowthReportRequest withPrevious(GrowthReportRequest request,
                                                    Map<String, Object> previous) {
        return new GrowthReportRequest(request.targetRole(), request.seniority(),
                request.resumeVersionId(), request.location(), request.currency(),
                request.targetSalary(), previous);
    }

    private void store(UUID userId, String role, Map<String, Object> report) {
        try {
            GrowthPlan row = new GrowthPlan();
            row.setUserId(userId);
            row.setTargetRole(role);
            row.setCoverage(coverageOf(report));
            row.setReport(report);
            plans.save(row);
        } catch (RuntimeException e) {
            // The user has the report; losing its history row must not turn a computed
            // answer into a 500. The next run simply diffs against nothing.
            log.warn("Storing the growth plan failed for user {}: {}", userId, e.toString());
        }
    }

    private static double coverageOf(Map<String, Object> report) {
        if (report == null) {
            return 0;
        }
        Object gap = report.get("gap");
        if (gap instanceof Map<?, ?> gapMap && gapMap.get("coverage") instanceof Number n) {
            return n.doubleValue();
        }
        return 0;
    }
}
