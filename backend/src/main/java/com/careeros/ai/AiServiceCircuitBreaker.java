package com.careeros.ai;

import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import io.github.resilience4j.circuitbreaker.CallNotPermittedException;
import java.util.function.Supplier;
import org.springframework.cloud.client.circuitbreaker.CircuitBreaker;
import org.springframework.cloud.client.circuitbreaker.CircuitBreakerFactory;
import org.springframework.stereotype.Component;

/**
 * The bridge to the ai-service stops knocking when nobody answers (Epic 85.1).
 *
 * <p>Every call in {@link HttpAiServiceClient} used to wait out its own timeout. When the
 * engine is down, that is the worst possible shape for a bridge: each request pays the
 * full connect/read budget, the visitor watches a spinner, and the backend's own threads
 * pile up behind a process that is not there. A circuit breaker turns "the engine is gone"
 * from a per-request discovery into a remembered fact: a handful of failures in a row open
 * the circuit, and while it is open a call fails in microseconds with the same 502 shape
 * the caller already understands.
 *
 * <p>The breaker wraps only the raw HTTP exchange, not its translation. That ordering is
 * deliberate: an answer that came back, even a refusal, is the engine working -- it must
 * not count towards opening the circuit (see {@code ignoreExceptions} in
 * {@code AiServiceResilienceConfig}) -- while a connection that never opened or a read
 * that timed out is exactly what the breaker exists to notice.
 *
 * <p>The guard is synchronous on purpose. The RestClient call already carries a 180-second
 * read timeout, so a second clock in another thread would duplicate the budget and drop
 * the request id out of the MDC; Spring Cloud's wrapper stays on the caller's thread when
 * no executor is configured, and this application configures none.
 */
@Component
public class AiServiceCircuitBreaker {

    /** The id the breaker registers under (and the name actuator health reports). */
    public static final String NAME = "ai-service";

    private final CircuitBreaker breaker;

    public AiServiceCircuitBreaker(CircuitBreakerFactory<?, ?> factory) {
        this.breaker = factory.create(NAME);
    }

    /**
     * Runs the exchange behind the breaker. Failures travel back unchanged -- the
     * translation to this service's error codes happens where it always did, outside --
     * except for the one case the breaker owns: while the circuit is open the call is not
     * attempted at all, and the caller hears the same 502 a failed attempt would have
     * produced, only immediately.
     */
    public <T> T call(Supplier<T> exchange) {
        try {
            return breaker.run(exchange, failure -> {
                throw rethrow(failure);
            });
        } catch (CallNotPermittedException resting) {
            throw new ApiException(ApiErrorCode.AI_SERVICE_UNAVAILABLE,
                    "AI service is resting after repeated failures");
        }
    }

    /** Keeps the original exception's type so the caller's catches still apply. */
    private static RuntimeException rethrow(Throwable failure) {
        if (failure instanceof RuntimeException runtime) {
            return runtime;
        }
        if (failure instanceof Error error) {
            throw error;
        }
        // A checked throwable cannot come out of the RestClient, but the guard is a
        // boundary and must still answer in this service's vocabulary. One literal
        // sentence per code is also what the error-code gate measures.
        return new ApiException(ApiErrorCode.AI_SERVICE_UNAVAILABLE, "AI service request failed");
    }
}
