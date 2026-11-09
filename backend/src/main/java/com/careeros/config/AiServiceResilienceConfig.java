package com.careeros.config;

import com.careeros.ai.AiServiceCircuitBreaker;
import io.github.resilience4j.circuitbreaker.CircuitBreakerConfig;
import java.time.Duration;
import java.util.List;
import java.util.concurrent.AbstractExecutorService;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.TimeUnit;
import org.springframework.cloud.client.circuitbreaker.Customizer;
import org.springframework.cloud.circuitbreaker.resilience4j.Resilience4JCircuitBreakerFactory;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestClientResponseException;

/**
 * The shape of the ai-service circuit (Epic 85.1).
 *
 * <p>Ten calls is the memory: long enough that one slow burst does not open the circuit,
 * short enough that a dead engine is noticed within a handful of visitors. Five calls is
 * the floor before the rate is trusted, half of them being failures is "the engine is
 * down rather than one query unlucky", and thirty seconds is how long the bridge waits
 * before a two-call half-open probe is allowed to ask again.
 *
 * <p>{@link RestClientResponseException} is ignored: the ai-service answering 400 or 404
 * is the engine working, and a circuit that opened on a visitor's malformed file would
 * punish everyone for one caller's typo. Connection refusals, resets and timeouts are the
 * failures that count.
 *
 * <p>A direct executor keeps the exchange on the caller's thread. Spring Cloud's factory
 * defaults to a cached thread pool, which would hand the HTTP call to a stranger: the
 * request id lives in the MDC (a ThreadLocal) and would not ride along, and the
 * RestClient's 180-second read budget would be re-timed by the wrapper's default one
 * second. The breaker is about remembering failure, not about moving work.
 */
@Configuration
public class AiServiceResilienceConfig {

    /** Runs a submitted task where it was submitted; see the class comment. */
    private static final ExecutorService CALLING_THREAD = new AbstractExecutorService() {
        @Override
        public void execute(Runnable command) {
            command.run();
        }

        @Override
        public void shutdown() {
        }

        @Override
        public List<Runnable> shutdownNow() {
            return List.of();
        }

        @Override
        public boolean isShutdown() {
            return false;
        }

        @Override
        public boolean isTerminated() {
            return false;
        }

        @Override
        public boolean awaitTermination(long timeout, TimeUnit unit) {
            return true;
        }
    };

    static final int SLIDING_WINDOW_SIZE = 10;
    static final int MINIMUM_NUMBER_OF_CALLS = 5;
    static final float FAILURE_RATE_THRESHOLD = 50f;
    static final Duration WAIT_DURATION_IN_OPEN_STATE = Duration.ofSeconds(30);
    static final int PERMITTED_CALLS_IN_HALF_OPEN_STATE = 2;

    @Bean
    public Customizer<Resilience4JCircuitBreakerFactory> aiServiceCircuitBreakerCustomizer() {
        return factory -> {
            factory.configureExecutorService(CALLING_THREAD);
            factory.configure(builder -> builder
                    .circuitBreakerConfig(CircuitBreakerConfig.custom()
                            .slidingWindowSize(SLIDING_WINDOW_SIZE)
                            .minimumNumberOfCalls(MINIMUM_NUMBER_OF_CALLS)
                            .failureRateThreshold(FAILURE_RATE_THRESHOLD)
                            .waitDurationInOpenState(WAIT_DURATION_IN_OPEN_STATE)
                            .permittedNumberOfCallsInHalfOpenState(PERMITTED_CALLS_IN_HALF_OPEN_STATE)
                            .ignoreExceptions(RestClientResponseException.class)
                            .build()),
                    AiServiceCircuitBreaker.NAME);
        };
    }
}
