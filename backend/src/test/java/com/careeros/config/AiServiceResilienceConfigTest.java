package com.careeros.config;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.careeros.ai.AiServiceCircuitBreaker;
import io.github.resilience4j.circuitbreaker.CircuitBreaker;
import io.github.resilience4j.circuitbreaker.CircuitBreakerConfig;
import io.github.resilience4j.circuitbreaker.CircuitBreakerRegistry;
import io.github.resilience4j.timelimiter.TimeLimiterRegistry;
import org.junit.jupiter.api.Test;
import org.springframework.cloud.circuitbreaker.resilience4j.Resilience4JCircuitBreakerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.ResourceAccessException;

/**
 * The ai-service breaker's shape as configured for production (Epic 85.1). The behaviour
 * is exercised in {@code AiServiceCircuitBreakerTest}; this pins the numbers an operator
 * would have to reason about when the engine goes quiet.
 */
class AiServiceResilienceConfigTest {

    @Test
    void theBreakerRemembersTenCallsAndRestsForThirtySeconds() {
        CircuitBreakerRegistry registry = CircuitBreakerRegistry.ofDefaults();
        Resilience4JCircuitBreakerFactory factory = new Resilience4JCircuitBreakerFactory(
                registry, TimeLimiterRegistry.ofDefaults(), null);
        new AiServiceResilienceConfig().aiServiceCircuitBreakerCustomizer().customize(factory);

        // One failing call registers the breaker in the registry; the run itself is beside
        // the point, the configuration it was built with is the subject.
        AiServiceCircuitBreaker guard = new AiServiceCircuitBreaker(factory);
        assertThatThrownBy(() -> guard.call(() -> {
            throw new ResourceAccessException("down");
        })).isInstanceOf(ResourceAccessException.class);

        CircuitBreaker breaker = registry.circuitBreaker(AiServiceCircuitBreaker.NAME);
        CircuitBreakerConfig config = breaker.getCircuitBreakerConfig();
        assertThat(config.getSlidingWindowSize())
                .isEqualTo(AiServiceResilienceConfig.SLIDING_WINDOW_SIZE)
                .isEqualTo(10);
        assertThat(config.getMinimumNumberOfCalls())
                .isEqualTo(AiServiceResilienceConfig.MINIMUM_NUMBER_OF_CALLS)
                .isEqualTo(5);
        assertThat(config.getFailureRateThreshold())
                .isEqualTo(AiServiceResilienceConfig.FAILURE_RATE_THRESHOLD)
                .isEqualTo(50f);
        assertThat(config.getPermittedNumberOfCallsInHalfOpenState())
                .isEqualTo(AiServiceResilienceConfig.PERMITTED_CALLS_IN_HALF_OPEN_STATE)
                .isEqualTo(2);
        assertThat(config.getWaitIntervalFunctionInOpenState().apply(1))
                .isEqualTo(AiServiceResilienceConfig.WAIT_DURATION_IN_OPEN_STATE.toMillis())
                .isEqualTo(30_000L);
    }

    @Test
    void onlyAnswersThatNeverCameCountAsFailures() {
        CircuitBreakerRegistry registry = CircuitBreakerRegistry.ofDefaults();
        Resilience4JCircuitBreakerFactory factory = new Resilience4JCircuitBreakerFactory(
                registry, TimeLimiterRegistry.ofDefaults(), null);
        new AiServiceResilienceConfig().aiServiceCircuitBreakerCustomizer().customize(factory);
        assertThatThrownBy(() -> new AiServiceCircuitBreaker(factory).call(() -> {
            throw new HttpClientErrorException(HttpStatus.BAD_REQUEST);
        })).isInstanceOf(HttpClientErrorException.class);

        CircuitBreakerConfig config = registry.circuitBreaker(AiServiceCircuitBreaker.NAME)
                .getCircuitBreakerConfig();
        // An answer -- even "no" -- is the engine working.
        assertThat(config.getIgnoreExceptionPredicate()
                .test(new HttpClientErrorException(HttpStatus.NOT_FOUND))).isTrue();
        // A socket that refused or a read that timed out is the failure worth remembering.
        assertThat(config.getIgnoreExceptionPredicate()
                .test(new ResourceAccessException("connection refused"))).isFalse();
    }
}
