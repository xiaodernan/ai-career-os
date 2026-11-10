package com.careeros.ai;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import io.github.resilience4j.circuitbreaker.CircuitBreaker;
import io.github.resilience4j.circuitbreaker.CircuitBreakerRegistry;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.cloud.circuitbreaker.resilience4j.Resilience4JCircuitBreakerFactory;

class AiServiceCircuitBreakerMetricsTest {

    @Test
    void gaugeIsZeroWhileNoBreakerIsOpen() {
        MeterRegistry meters = new SimpleMeterRegistry();
        ObjectProvider<CircuitBreakerRegistry> provider = mock(ObjectProvider.class);
        CircuitBreakerRegistry registry = CircuitBreakerRegistry.ofDefaults();
        when(provider.getIfAvailable()).thenReturn(registry);

        new AiServiceCircuitBreakerMetrics(meters, provider, mock(ObjectProvider.class));

        assertThat(meters.get("careeros.circuitbreaker.open").gauge().value()).isEqualTo(0.0);
    }

    @Test
    void gaugeIsOneWhileABreakerIsOpen() {
        MeterRegistry meters = new SimpleMeterRegistry();
        CircuitBreakerRegistry registry = CircuitBreakerRegistry.ofDefaults();
        ObjectProvider<CircuitBreakerRegistry> provider = mock(ObjectProvider.class);
        when(provider.getIfAvailable()).thenReturn(registry);

        new AiServiceCircuitBreakerMetrics(meters, provider, mock(ObjectProvider.class));

        CircuitBreaker breaker = registry.circuitBreaker("ai-service");
        breaker.transitionToForcedOpenState();

        assertThat(meters.get("careeros.circuitbreaker.open").gauge().value()).isEqualTo(1.0);

        breaker.transitionToClosedState();
        assertThat(meters.get("careeros.circuitbreaker.open").gauge().value()).isEqualTo(0.0);
    }
}