package com.careeros.gateway;

import io.github.resilience4j.circuitbreaker.CircuitBreakerConfig;
import java.time.Duration;
import org.springframework.cloud.circuitbreaker.resilience4j.ReactiveResilience4JCircuitBreakerFactory;
import org.springframework.cloud.circuitbreaker.resilience4j.Resilience4JConfigBuilder;
import org.springframework.cloud.client.circuitbreaker.Customizer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * The circuit in front of the domain backend (Epic 88.2).
 *
 * <p>Ten calls is the memory, five the floor before the failure rate is trusted, half of
 * them being failures is "the backend is down rather than one request unlucky", and
 * thirty seconds is how long the edge waits before a half-open probe may ask again. The
 * shape is the backend's own ai-service circuit (85.1) on purpose: one vocabulary for
 * "quiet neighbour" across both processes.
 *
 * <p>The factory is the reactive one. The gateway's chain runs on the event loop, and the
 * servlet-era factory the backend uses would wrap a blocking call in an exchange that
 * never blocks -- the circuit would measure the wrong thing or not at all.
 */
@Configuration
public class GatewayResilienceConfig {

    static final int SLIDING_WINDOW_SIZE = 10;
    static final int MINIMUM_NUMBER_OF_CALLS = 5;
    static final float FAILURE_RATE_THRESHOLD = 50f;
    static final Duration WAIT_DURATION_IN_OPEN_STATE = Duration.ofSeconds(30);
    static final int PERMITTED_CALLS_IN_HALF_OPEN_STATE = 3;

    @Bean
    public Customizer<ReactiveResilience4JCircuitBreakerFactory> backendCircuitCustomizer() {
        return factory -> {
            CircuitBreakerConfig shape = CircuitBreakerConfig.custom()
                    .slidingWindowSize(SLIDING_WINDOW_SIZE)
                    .minimumNumberOfCalls(MINIMUM_NUMBER_OF_CALLS)
                    .failureRateThreshold(FAILURE_RATE_THRESHOLD)
                    .waitDurationInOpenState(WAIT_DURATION_IN_OPEN_STATE)
                    .permittedNumberOfCallsInHalfOpenState(PERMITTED_CALLS_IN_HALF_OPEN_STATE)
                    .build();
            factory.configureDefault(id -> new Resilience4JConfigBuilder(id)
                    .circuitBreakerConfig(shape)
                    .build());
        };
    }
}
