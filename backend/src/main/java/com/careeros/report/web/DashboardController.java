package com.careeros.report.web;

import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import com.careeros.report.dto.ActivityHeatmapDtos.ActivityHeatmapResponse;
import com.careeros.report.dto.DashboardDtos.DashboardResponse;
import com.careeros.report.service.ActivityHeatmapService;
import com.careeros.report.service.DashboardService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/reports")
public class DashboardController {

    private final DashboardService dashboard;
    private final ActivityHeatmapService heatmap;

    public DashboardController(DashboardService dashboard, ActivityHeatmapService heatmap) {
        this.dashboard = dashboard;
        this.heatmap = heatmap;
    }

    @GetMapping("/dashboard")
    public DashboardResponse dashboard(@CurrentUser AuthUser user) {
        return dashboard.build(user.id());
    }

    /** The reader's pace as one dense day-grid (Epic 184); the window clamps in the service. */
    @GetMapping("/activity-heatmap")
    public ActivityHeatmapResponse activityHeatmap(@CurrentUser AuthUser user,
                                                   @RequestParam(defaultValue = "182") int days) {
        return heatmap.build(user.id(), days);
    }
}
