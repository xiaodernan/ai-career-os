package com.careeros.report.web;

import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import com.careeros.common.PageDTO;
import com.careeros.report.dto.NightlyReportDtos.NightlyReportItem;
import com.careeros.report.dto.NightlyReportDtos.NightlyVerdict;
import com.careeros.report.service.MonitoringService;
import com.careeros.report.service.NightlyReportService;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * Production monitoring (16.1): agent health, cost, and regression detection.
 *
 * <p>The health report is read-only and deterministic — the engine reads the user's
 * own agent runs and usage events and computes metrics without a model. This route
 * answers the report the engine built, in the engine's own shape.
 *
 * <p>The nightly history (20.1) is the other half of "is the platform healthy": not the
 * user's agent runs but the deployment's own verification, one row per night. It is
 * deployment-wide rather than per user — the same history for every reader, which is what
 * makes it a record of the install instead of a record of one person's work.
 */
@RestController
@RequestMapping("/api/v1/monitoring")
public class MonitoringController {

    private final MonitoringService monitoring;
    private final NightlyReportService nightlyReports;

    public MonitoringController(MonitoringService monitoring, NightlyReportService nightlyReports) {
        this.monitoring = monitoring;
        this.nightlyReports = nightlyReports;
    }

    @GetMapping("/health-report")
    public Map<String, Object> healthReport(@CurrentUser AuthUser user) {
        return monitoring.healthReport(user.id());
    }

    @GetMapping("/nightly-reports")
    public PageDTO<NightlyReportItem> nightlyHistory(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size) {
        return nightlyReports.list(page, size);
    }

    /** Whether the install verified itself, without paging the history (20.2). */
    @GetMapping("/nightly-reports/verdict")
    public NightlyVerdict nightlyVerdict() {
        return nightlyReports.verdict();
    }
}
