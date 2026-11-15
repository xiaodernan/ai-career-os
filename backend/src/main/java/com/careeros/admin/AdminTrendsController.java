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

    public AdminTrendsController(AdminTrendsService trends, AdminFreshnessService freshness) {
        this.trends = trends;
        this.freshness = freshness;
    }

    @GetMapping("/trends")
    public Map<String, Object> trends(@RequestParam(defaultValue = "12") int weeks) {
        return trends.trends(weeks);
    }

    @GetMapping("/freshness")
    public Map<String, Object> freshness() {
        return freshness.freshness();
    }
}
