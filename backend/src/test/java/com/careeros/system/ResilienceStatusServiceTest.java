package com.careeros.system;

import static org.assertj.core.api.Assertions.assertThat;

import io.github.resilience4j.circuitbreaker.CircuitBreaker;
import io.github.resilience4j.circuitbreaker.CircuitBreakerRegistry;
import java.util.Map;
import org.junit.jupiter.api.Test;

class ResilienceStatusServiceTest {

    @Test
    void reportListsBreakerStateAndMetrics() {
        CircuitBreakerRegistry registry = CircuitBreakerRegistry.ofDefaults();
        CircuitBreaker cb = registry.circuitBreaker("ai-service");
        cb.onError(0, java.util.concurrent.TimeUnit.MILLISECONDS, new RuntimeException("boom"));

        ResilienceStatusService service = new ResilienceStatusService(registry);
        Map<String, Object> report = service.report();

        assertThat(report).containsKey("circuitBreakers");
        @SuppressWarnings("unchecked")
        var breakers = (java.util.List<Map<String, Object>>) report.get("circuitBreakers");
        assertThat(breakers).isNotEmpty();
        Map<String, Object> row = breakers.stream()
                .filter(r -> "ai-service".equals(r.get("name")))
                .findFirst()
                .orElseThrow();
        assertThat(row.get("state")).isIn("CLOSED", "OPEN", "HALF_OPEN", "DISABLED", "FORCED_OPEN", "METRICS_ONLY");
        assertThat(row).containsKeys("failureRate", "numberOfBufferedCalls", "numberOfFailedCalls",
                "numberOfSuccessfulCalls", "numberOfNotPermittedCalls");
    }
}
