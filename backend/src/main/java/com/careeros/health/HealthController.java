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
     * The readiness report. Always 200, whatever it says -- the body is the message,
     * and a probe that refuses to answer cannot tell a monitor which half is missing.
     * The report is burst-cached for two seconds: a dashboard that fans out to every
     * replica at once reads one probe's answer, not one hundred's.
     */
    @GetMapping
    public Map<String, Object> health() {
        return health.reportCached();
    }

    /** The liveness line: no dependency is asked. Fails only when this JVM does. */
    @GetMapping("/live")
    public Map<String, Object> live() {
        return health.liveness();
    }
}
