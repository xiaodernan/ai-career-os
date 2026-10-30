package com.careeros.health;

import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/health")
public class HealthController {

    private final HealthService health;

    public HealthController(HealthService health) {
        this.health = health;
    }

    /**
     * The deployment's own report: the database, Redis, the object store and the ai-service,
     * each true or false, with one verdict over them. Always 200, whatever it says -- the
     * body is the message, and a probe that refuses to answer cannot tell a monitor which
     * half is missing. The work behind it lives in {@link HealthService}, where each probe
     * is bounded so a hung dependency cannot hang the route.
     */
    @GetMapping
    public Map<String, Object> health() {
        return health.report();
    }
}
