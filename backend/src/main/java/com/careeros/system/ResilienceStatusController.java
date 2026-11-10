package com.careeros.system;

import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Resilience state for operators (Epic 105).
 *
 * <p>Exposes Spring Cloud / Resilience4j circuit breaker states for the ai-service bridge
 * so an operator can see which doors are closed, open or half-open without scraping
 * internals. Same auth boundary as the rest of the API.
 */
@RestController
@RequestMapping("/api/v1/system")
public class ResilienceStatusController {

    private final ResilienceStatusService resilience;

    public ResilienceStatusController(ResilienceStatusService resilience) {
        this.resilience = resilience;
    }

    @GetMapping("/resilience")
    public Map<String, Object> resilience() {
        return resilience.report();
    }
}
