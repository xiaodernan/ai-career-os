package com.careeros.system;

import io.github.resilience4j.circuitbreaker.CircuitBreaker;
import io.github.resilience4j.circuitbreaker.CircuitBreakerRegistry;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.cloud.circuitbreaker.resilience4j.Resilience4JCircuitBreakerFactory;
import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Autowired;

/**
 * Spring Cloud Resilience4j circuit breaker states (Epic 105).
 *
 * <p>The ai-service bridge keeps one breaker per origin and one whole-bridge breaker; their
 * states are useful to operators when a replica is resting. The registry is the source of
 * truth for breakers created through the Resilience4j factory.
 */
@Service
public class ResilienceStatusService {

    private final CircuitBreakerRegistry registry;

    // Two constructors exist (the package-private one is the test seam), so Spring must be
    // told which one it wants -- an unannotated class with two constructors falls back to
    // looking for a default one and fails the context with "No default constructor found".
    @Autowired
    public ResilienceStatusService(ObjectProvider<CircuitBreakerRegistry> registryProvider,
                                   ObjectProvider<Resilience4JCircuitBreakerFactory> factoryProvider) {
        CircuitBreakerRegistry registry = registryProvider.getIfAvailable();
        if (registry == null) {
            Resilience4JCircuitBreakerFactory factory = factoryProvider.getIfAvailable();
            registry = factory != null ? factory.getCircuitBreakerRegistry() : CircuitBreakerRegistry.ofDefaults();
        }
        this.registry = registry;
    }

    ResilienceStatusService(CircuitBreakerRegistry registry) {
        this.registry = registry;
    }

    public Map<String, Object> report() {
        Map<String, Object> body = new LinkedHashMap<>();
        List<Map<String, Object>> breakers = registry.getAllCircuitBreakers().stream()
                .map(this::row)
                .sorted((a, b) -> String.valueOf(a.get("name")).compareToIgnoreCase(String.valueOf(b.get("name"))))
                .toList();
        body.put("circuitBreakers", breakers);
        return body;
    }

    private Map<String, Object> row(CircuitBreaker breaker) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("name", breaker.getName());
        row.put("state", breaker.getState().name());
        CircuitBreaker.Metrics metrics = breaker.getMetrics();
        row.put("failureRate", metrics.getFailureRate());
        row.put("numberOfBufferedCalls", metrics.getNumberOfBufferedCalls());
        row.put("numberOfFailedCalls", metrics.getNumberOfFailedCalls());
        row.put("numberOfSuccessfulCalls", metrics.getNumberOfSuccessfulCalls());
        row.put("numberOfNotPermittedCalls", metrics.getNumberOfNotPermittedCalls());
        return row;
    }
}
