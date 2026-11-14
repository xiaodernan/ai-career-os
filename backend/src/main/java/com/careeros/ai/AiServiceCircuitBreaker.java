package com.careeros.ai;

import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import io.github.resilience4j.circuitbreaker.CallNotPermittedException;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Semaphore;
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
 *
 * <p>Since 87.1 the guard remembers failure per door, not for the fleet. With one breaker
 * for every instance, a dead replica's refusals opened the circuit for the healthy ones
 * too -- the bridge rested while most of the engine was answering. Each origin now gets
 * its own breaker (the same tuned shape), so a quiet node rests alone and the balancer's
 * next choice is still allowed to work.
 *
 * <p>Since Epic 203 the guard also holds a roof. A breaker remembers failure; it does not
 * stop a flood from arriving. When the engine slows, every in-flight call pins a backend
 * thread for the length of the wait, and the request queue behind the engine fills with
 * visitors waiting two minutes each. A fair semaphore caps the in-flight count at sixteen:
 * the seventeenth concurrent call is refused in microseconds with the same 503 shape the
 * caller already understands ({@code AI_SERVICE_UNAVAILABLE}) instead of queued behind a
 * timeout nobody is home for. No wait, by design — a caller that cannot have a permit now
 * is not blocked, because a permit that will free up inside the visitor's own patience
 * cannot be promised by anyone. The permit is taken before the breaker runs and released
 * when the exchange ends, success or failure; resting breakers are checked inside the
 * permit, so an open circuit still costs one permit briefly, never a queue.
 */
@Component
public class AiServiceCircuitBreaker {

    /** The id the whole-bridge breaker registers under (and the name actuator health reports). */
    public static final String NAME = "ai-service";

    /**
     * The roof. Sixteen in flight at once: well under the Tomcat default (200 threads), generous
     * against this app's own per-user bridge budget, and small enough that a slow engine empties
     * its queue to refusal rather than to a two-minute wait for everyone.
     */
    public static final int MAX_CONCURRENT = 16;

    private final CircuitBreakerFactory<?, ?> factory;
    private final CircuitBreaker breaker;
    /**
     * One breaker per origin, created on first use; the fleet's list is small and fixed.
     */
    private final ConcurrentHashMap<String, CircuitBreaker> perNode = new ConcurrentHashMap<>();
    /**
     * Fair: permits are handed out in arrival order, so a sustained flood cannot starve the
     * visitor who arrived first. Unfair semaphores favour the last arrival on a full queue and
     * starve the first one out for no reason a reader could see.
     */
    private final Semaphore permits = new Semaphore(MAX_CONCURRENT, true);

    public AiServiceCircuitBreaker(CircuitBreakerFactory<?, ?> factory) {
        this.factory = factory;
        this.breaker = factory.create(NAME);
    }

    /** The whole-bridge question, kept for callers that have no door to name. */
    public <T> T call(Supplier<T> exchange) {
        return call(NAME, exchange);
    }

    /**
     * Runs the exchange behind the roof and then the breaker of the node it is addressed to.
     *
     * <p>An unknown or blank origin falls back to the whole-bridge breaker: a caller that
     * cannot say which door it used is asking the old question, and must not silently get
     * a fresh breaker per call.
     */
    public <T> T call(String node, Supplier<T> exchange) {
        CircuitBreaker at = node == null || node.isBlank() || NAME.equals(node)
                ? breaker
                : perNode.computeIfAbsent(node, factory::create);
        if (!permits.tryAcquire()) {
            throw new ApiException(ApiErrorCode.AI_SERVICE_UNAVAILABLE,
                    "AI service is at capacity; try again shortly");
        }
        try {
            return at.run(exchange, failure -> {
                throw rethrow(failure);
            });
        } catch (CallNotPermittedException resting) {
            throw new ApiException(ApiErrorCode.AI_SERVICE_UNAVAILABLE,
                    "AI service is resting after repeated failures");
        } finally {
            permits.release();
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
