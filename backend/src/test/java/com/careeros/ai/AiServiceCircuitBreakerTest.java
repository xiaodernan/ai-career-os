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
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Supplier;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.cloud.circuitbreaker.resilience4j.Resilience4JCircuitBreakerFactory;
import org.springframework.cloud.circuitbreaker.resilience4j.Resilience4JConfigBuilder;
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

    @Test
    void oneQuietDoorRestsAloneAndTheFleetKeepsAnswering() {
        AiServiceCircuitBreaker guard = guard();
        Supplier<String> dead = () -> {
            throw new ResourceAccessException("connection refused");
        };

        assertThatThrownBy(() -> guard.call("http://a:8000", dead))
                .isInstanceOf(ResourceAccessException.class);
        assertThatThrownBy(() -> guard.call("http://a:8000", dead))
                .isInstanceOf(ResourceAccessException.class);
        assertThat(registry.circuitBreaker("http://a:8000").getState())
                .isEqualTo(CircuitBreaker.State.OPEN);

        // Nothing was charged to the whole-bridge breaker: the failure belongs to a node.
        assertThat(registry.circuitBreaker(AiServiceCircuitBreaker.NAME).getState())
                .isEqualTo(CircuitBreaker.State.CLOSED);
        assertThat(guard.call("http://b:8000", () -> "parsed")).isEqualTo("parsed");
        assertThat(guard.call("http://b:8000", () -> "parsed")).isEqualTo("parsed");
        assertThat(registry.circuitBreaker("http://b:8000").getState())
                .isEqualTo(CircuitBreaker.State.CLOSED);

        // The quiet door is refused by its own breaker: the supplier is never entered.
        AtomicInteger attempts = new AtomicInteger();
        assertThatThrownBy(() -> guard.call("http://a:8000", () -> {
            attempts.incrementAndGet();
            return "should not run";
        })).isInstanceOf(ApiException.class)
                .hasMessageContaining("resting");
        assertThat(attempts).hasValue(0);
    }

    @Test
    void theSeventeenthConcurrentCallIsRefusedWithoutQueuing() throws Exception {
        AiServiceCircuitBreaker guard = guard();
        int max = AiServiceCircuitBreaker.MAX_CONCURRENT;
        CountDownLatch inFlight = new CountDownLatch(max);
        CountDownLatch release = new CountDownLatch(1);
        ExecutorService pool = Executors.newFixedThreadPool(max);
        List<Future<Object>> held = new ArrayList<>();
        try {
            for (int i = 0; i < max; i++) {
                held.add(pool.submit(() -> guard.call(() -> {
                    inFlight.countDown();
                    try {
                        release.await(5, TimeUnit.SECONDS);
                    } catch (InterruptedException e) {
                        throw new AssertionError(e);
                    }
                    return (Object) "held";
                })));
            }
            assertThat(inFlight.await(5, TimeUnit.SECONDS))
                    .as("all %d seats are in flight", max)
                    .isTrue();

            // #17: the visitor behind the flood is refused in microseconds and the engine is
            // never entered on its behalf.
            ApiException refused = null;
            try {
                guard.call(() -> {
                    throw new AssertionError("the engine must not be entered at capacity");
                });
            } catch (ApiException e) {
                refused = e;
            }
            assertThat(refused).isNotNull();
            assertThat(refused.code()).isEqualTo(ApiErrorCode.AI_SERVICE_UNAVAILABLE);
            assertThat(refused).hasMessageContaining("capacity");

            release.countDown();
            for (Future<Object> f : held) {
                assertThat(f.get(5, TimeUnit.SECONDS)).isEqualTo("held");
            }
            // The seats are all back: the next sixteen calls sail through.
            for (int i = 0; i < max; i++) {
                assertThat(guard.call(() -> "ok")).isEqualTo("ok");
            }
        } finally {
            release.countDown();
            pool.shutdownNow();
        }
    }

    @Test
    void noPermitLeaksAcrossFortyEightFailingCalls() {
        AiServiceCircuitBreaker guard = guard();
        // The test-shape breaker opens at two failures; after that the engine is unreachable
        // anyway. What must never appear is a "capacity" refusal: a leaked permit would
        // exhaust the sixteen seats and refuse a visitor who never entered the engine.
        int capacityRefusals = 0;
        for (int i = 0; i < 48; i++) {
            try {
                guard.call(() -> {
                    throw new ResourceAccessException("connection refused");
                });
            } catch (ApiException e) {
                if (e.getMessage() != null && e.getMessage().contains("capacity")) {
                    capacityRefusals++;
                }
            } catch (ResourceAccessException expected) {
                // the engine was reached and answered no, as designed
            }
        }
        assertThat(capacityRefusals).isZero();
    }

    /**
     * The production shape, in miniature: four calls in the window, two needed before the
     * rate is trusted. Small numbers keep the test fast; the thresholds themselves are
     * pinned in {@code AiServiceResilienceConfigTest}.
     */
    private AiServiceCircuitBreaker guard() {
        // Default, because the guard creates a breaker per door from this same shape.
        factory.configureDefault(id -> new Resilience4JConfigBuilder(id)
                .circuitBreakerConfig(CircuitBreakerConfig.custom()
                        .slidingWindowSize(4)
                        .minimumNumberOfCalls(2)
                        .failureRateThreshold(50)
                        .waitDurationInOpenState(Duration.ofSeconds(30))
                        .permittedNumberOfCallsInHalfOpenState(2)
                        .ignoreExceptions(RestClientResponseException.class)
                        .build())
                .build());
        return new AiServiceCircuitBreaker(factory);
    }

    private CircuitBreaker breaker() {
        return registry.circuitBreaker(AiServiceCircuitBreaker.NAME);
    }
}
