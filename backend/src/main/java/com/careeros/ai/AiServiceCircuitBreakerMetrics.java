package com.careeros.ai;

import io.github.resilience4j.circuitbreaker.CircuitBreaker;
import io.github.resilience4j.circuitbreaker.CircuitBreakerRegistry;
import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import org.springframework.boot.actuate.info.Info;
import org.springframework.boot.actuate.info.InfoContributor;
import org.springframework.cloud.circuitbreaker.resilience4j.Resilience4JCircuitBreakerFactory;
import org.springframework.stereotype.Component;
import org.springframework.beans.factory.ObjectProvider;

/**
 * A gauge the alarm reads, not a page the operator reads (Epic 108.24).
 *
 * <p>The api's {@code AiServiceCircuitBreaker} guards the ai-service bridge per origin. The ops
 * surface (`/actuator/circuitbreakers`, `/api/v1/system/resilience`) already shows a snapshot of
 * the breaker's state when an operator asks — but an operator does not ask until they know to.
 * This gauge is the continuous version: 1 while any breaker in the live registry is open,
 * 0 otherwise. Prometheus turns it into the series the `CareerOSCircuitBreakerOpen` alarm reads;
 * the alert that follows it fires only when the bridge's refusal is sustained.
 */
@Component
public class AiServiceCircuitBreakerMetrics implements InfoContributor {

    private final CircuitBreakerRegistry registry;

    public AiServiceCircuitBreakerMetrics(MeterRegistry meters,
                                          ObjectProvider<CircuitBreakerRegistry> registryProvider,
                                          ObjectProvider<Resilience4JCircuitBreakerFactory> factoryProvider) {
        CircuitBreakerRegistry resolved = registryProvider.getIfAvailable();
        if (resolved == null) {
            Resilience4JCircuitBreakerFactory factory = factoryProvider.getIfAvailable();
            resolved = factory != null ? factory.getCircuitBreakerRegistry() : CircuitBreakerRegistry.ofDefaults();
        }
        this.registry = resolved;
        Gauge.builder("careeros.circuitbreaker.open", registry, self -> self.getAllCircuitBreakers().stream()
                        .filter(AiServiceCircuitBreakerMetrics::isOpen)
                        .findAny()
                        .map(cb -> 1.0)
                        .orElse(0.0))
                .description("1 while any ai-service circuit breaker is open, 0 otherwise")
                .register(meters);
    }

    @Override
    public void contribute(Info.Builder builder) {
        builder.withDetail("circuitBreakerOpen", isOpen());
    }

    private boolean isOpen() {
        return registry.getAllCircuitBreakers().stream().anyMatch(AiServiceCircuitBreakerMetrics::isOpen);
    }

    private static boolean isOpen(CircuitBreaker breaker) {
        return breaker.getState() == CircuitBreaker.State.OPEN
                || breaker.getState() == CircuitBreaker.State.FORCED_OPEN;
    }
}