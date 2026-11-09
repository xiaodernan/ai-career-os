package com.careeros.ai;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import io.github.resilience4j.circuitbreaker.CircuitBreaker;
import io.github.resilience4j.circuitbreaker.CircuitBreakerConfig;
import io.github.resilience4j.circuitbreaker.CircuitBreakerRegistry;
import io.github.resilience4j.timelimiter.TimeLimiterRegistry;
import java.time.Duration;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Supplier;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.cloud.circuitbreaker.resilience4j.Resilience4JCircuitBreakerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClientResponseException;

/**
 * The guard in front of the ai-service bridge (Epic 85.1).
 *
 * <p>The rule under test is not "a circuit breaker exists" but the one that makes it worth
 * having: after the engine has failed enough times in a row, the next call must not reach
 * the socket at all, and the caller must hear the same 502 it would have heard anyway,
 * only without the wait. The mirror rule matters just as much: an engine that answers
 * "no" (a refusal) is working, and opening the circuit over a visitor's malformed file
 * would take the product down for everyone because one caller made a typo.
 */
class AiServiceCircuitBreakerTest {

    private CircuitBreakerRegistry registry;
    private Resilience4JCircuitBreakerFactory factory;

    @BeforeEach
    void setUp() {
        registry = CircuitBreakerRegistry.ofDefaults();
        factory = new Resilience4JCircuitBreakerFactory(
                registry, TimeLimiterRegistry.ofDefaults(), null);
    }

    @Test
    void aCallThatWorksComesBackAsItIs() {
        AiServiceCircuitBreaker guard = guard();
        assertThat(guard.call(() -> "parsed")).isEqualTo("parsed");
        assertThat(breaker().getMetrics().getNumberOfSuccessfulCalls()).isEqualTo(1);
    }

    @Test
    void theCircuitOpensAfterRepeatedFailuresAndTheNextCallNeverLeaves() {
        AiServiceCircuitBreaker guard = guard();
        AtomicInteger attempts = new AtomicInteger();
        Supplier<String> engineIsGone = () -> {
            attempts.incrementAndGet();
            throw new ResourceAccessException("connection refused");
        };

        // Two calls exceed the window's failure threshold (100% of two calls >= 50%).
        assertThatThrownBy(() -> guard.call(engineIsGone))
                .isInstanceOf(ResourceAccessException.class);
        assertThatThrownBy(() -> guard.call(engineIsGone))
                .isInstanceOf(ResourceAccessException.class);
        assertThat(breaker().getState()).isEqualTo(CircuitBreaker.State.OPEN);

        // The third one is refused by the guard itself: the supplier is never entered.
        ApiException refused = null;
        try {
            guard.call(engineIsGone);
        } catch (ApiException e) {
            refused = e;
        }
        assertThat(refused).isNotNull();
        assertThat(refused.code()).isEqualTo(ApiErrorCode.AI_SERVICE_UNAVAILABLE);
        assertThat(refused).hasMessageContaining("resting");
        assertThat(attempts).hasValue(2);
        assertThat(breaker().getMetrics().getNumberOfNotPermittedCalls()).isEqualTo(1);
    }

    @Test
    void anUpstreamRefusalIsTheEngineWorkingAndDoesNotOpenTheCircuit() {
        AiServiceCircuitBreaker guard = guard();

        // A refusal crossed the socket: the engine read the request and said no.
        for (int i = 0; i < 6; i++) {
            assertThatThrownBy(() -> guard.call(() -> {
                throw new HttpClientErrorException(HttpStatus.BAD_REQUEST);
            })).isInstanceOf(RestClientResponseException.class);
        }

        assertThat(breaker().getState()).isEqualTo(CircuitBreaker.State.CLOSED);
        assertThat(breaker().getMetrics().getNumberOfFailedCalls()).isZero();
    }

    @Test
    void aClosedCircuitRemembersAgainAfterTheEngineReturns() {
        AiServiceCircuitBreaker guard = guard();
        Supplier<String> engineIsGone = () -> {
            throw new ResourceAccessException("connection refused");
        };
        assertThatThrownBy(() -> guard.call(engineIsGone)).isInstanceOf(ResourceAccessException.class);
        assertThatThrownBy(() -> guard.call(engineIsGone)).isInstanceOf(ResourceAccessException.class);
        assertThat(breaker().getState()).isEqualTo(CircuitBreaker.State.OPEN);

        // Deterministic half-open: no sleep, the registry is asked to probe now.
        breaker().transitionToHalfOpenState();
        assertThat(guard.call(() -> "back")).isEqualTo("back");
        assertThat(guard.call(() -> "back")).isEqualTo("back");
        assertThat(breaker().getState()).isEqualTo(CircuitBreaker.State.CLOSED);
    }

    /**
     * The production shape, in miniature: four calls in the window, two needed before the
     * rate is trusted. Small numbers keep the test fast; the thresholds themselves are
     * pinned in {@code AiServiceResilienceConfigTest}.
     */
    private AiServiceCircuitBreaker guard() {
        factory.configure(builder -> builder
                .circuitBreakerConfig(CircuitBreakerConfig.custom()
                        .slidingWindowSize(4)
                        .minimumNumberOfCalls(2)
                        .failureRateThreshold(50)
                        .waitDurationInOpenState(Duration.ofSeconds(30))
                        .permittedNumberOfCallsInHalfOpenState(2)
                        .ignoreExceptions(RestClientResponseException.class)
                        .build()),
                AiServiceCircuitBreaker.NAME);
        return new AiServiceCircuitBreaker(factory);
    }

    private CircuitBreaker breaker() {
        return registry.circuitBreaker(AiServiceCircuitBreaker.NAME);
    }
}
