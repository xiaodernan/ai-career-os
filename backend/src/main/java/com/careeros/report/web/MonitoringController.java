package com.careeros.report.web;

import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import com.careeros.report.service.MonitoringService;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Production monitoring (16.1): agent health, cost, and regression detection.
 *
 * <p>The health report is read-only and deterministic — the engine reads the user's
 * own agent runs and usage events and computes metrics without a model. This route
 * answers the report the engine built, in the engine's own shape.
 */
@RestController
@RequestMapping("/api/v1/monitoring")
public class MonitoringController {

    private final MonitoringService monitoring;

    public MonitoringController(MonitoringService monitoring) {
        this.monitoring = monitoring;
    }

    @GetMapping("/health-report")
    public Map<String, Object> healthReport(@CurrentUser AuthUser user) {
        return monitoring.healthReport(user.id());
    }
}
