package com.careeros.admin;

import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * The weekly trend line the overseer watches (Epic 251).
 *
 * <p>Same privacy posture as {@link AdminStatsController}: five series of counts, bucketed
 * by ISO week. Nothing per reader, nothing now-in-the-future — the historical rows only.
 */
@RestController
@RequestMapping("/api/v1/admin")
public class AdminTrendsController {

    private final AdminTrendsService trends;
    private final AdminFreshnessService freshness;
    private final AdminFunnelService funnel;
    private final AdminCohortService cohort;
    private final AdminRhythmService rhythm;

    public AdminTrendsController(AdminTrendsService trends, AdminFreshnessService freshness, AdminFunnelService funnel, AdminCohortService cohort, AdminRhythmService rhythm) {
        this.trends = trends;
        this.freshness = freshness;
        this.funnel = funnel;
        this.cohort = cohort;
        this.rhythm = rhythm;
    }

    @GetMapping("/trends")
    public Map<String, Object> trends(@RequestParam(defaultValue = "12") int weeks) {
        return trends.trends(weeks);
    }

    @GetMapping("/cohort")
    public Map<String, Object> cohort(@RequestParam(defaultValue = "12") int weeks) {
        return cohort.cohort(weeks);
    }

    @GetMapping("/freshness")
    public Map<String, Object> freshness() {
        return freshness.freshness();
    }

    @GetMapping("/funnel")
    public Map<String, Object> funnel() {
        return funnel.funnel();
    }

    @GetMapping("/rhythm")
    public Map<String, Object> rhythm(@RequestParam(defaultValue = "28") int days) {
        return rhythm.rhythm(days);
    }
}
