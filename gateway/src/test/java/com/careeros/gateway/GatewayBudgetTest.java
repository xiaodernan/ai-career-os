package com.careeros.gateway;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;

import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.support.StaticListableBeanFactory;
import org.springframework.data.redis.connection.ReactiveRedisConnectionFactory;
import org.springframework.data.redis.core.ReactiveStringRedisTemplate;
import org.springframework.data.redis.core.script.RedisScript;
import org.springframework.http.HttpStatus;
import org.springframework.mock.http.server.reactive.MockServerHttpRequest;
import org.springframework.mock.web.server.MockServerWebExchange;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

/**
 * Epic 120 — the edge's allowance is one allowance, and its failure is a fallback.
 *
 * <p>These cases are about the *decision*, not about Redis: a filter that consults a
 * shared budget only when asked, a refusal that never reaches the backend, and a shared
 * budget that throws being answered by this process instead of by an open door. The
 * script itself is pinned separately: one call, one key, three arguments -- a
 * read-refill-write spread over several round trips is the race this design exists to
 * avoid, so the shape is asserted rather than trusted.
 */
class GatewayBudgetTest {

    private static ObjectProvider<EdgeBudget> provider(EdgeBudget budget) {
        StaticListableBeanFactory factory = new StaticListableBeanFactory(Map.of("shared", budget));
        return factory.getBeanProvider(EdgeBudget.class);
    }

    private static GatewayRateLimitFilter filter(int tokens, Duration period, EdgeBudget shared,
                                                 boolean distributed) {
        return new GatewayRateLimitFilter(tokens, period, new SimpleMeterRegistry(),
                shared == null ? null : provider(shared), distributed);
    }

    private static EdgeBudget stub(boolean answer) {
        return new EdgeBudget() {
            final AtomicInteger asks = new AtomicInteger();

            @Override
            public Mono<Boolean> take(String identity) {
                asks.incrementAndGet();
                return Mono.just(answer);
            }

            @Override
            public String name() {
                return "redis";
            }
        };
    }

    @Test
    void withoutTheFlagTheEdgeNeverAsksTheSharedBudget() {
        EdgeBudget shared = stub(true);
        GatewayRateLimitFilter edge = filter(5, Duration.ofSeconds(1), shared, false);

        assertThat(edge.budgetInUse()).isEqualTo("in-process");
        run(edge);
        assertThat(((AtomicInteger) field(shared, "asks")).get()).isZero();
    }

    @Test
    void withTheFlagTheDecisionIsTheSharedOne() {
        EdgeBudget shared = stub(true);
        GatewayRateLimitFilter edge = filter(5, Duration.ofSeconds(1), shared, true);

        assertThat(edge.budgetInUse()).isEqualTo("redis");
        assertThat(run(edge).getAttributes().get("test.forwarded")).isEqualTo(true);
        assertThat(((AtomicInteger) field(shared, "asks")).get()).isEqualTo(1);
    }

    @Test
    void aFailedSharedBudgetIsAnsweredHereAndCounted() {
        EdgeBudget broken = new EdgeBudget() {
            @Override
            public Mono<Boolean> take(String identity) {
                return Mono.error(new IllegalStateException("redis refused"));
            }

            @Override
            public String name() {
                return "redis";
            }
        };
        SimpleMeterRegistry meters = new SimpleMeterRegistry();
        GatewayRateLimitFilter edge = new GatewayRateLimitFilter(5, Duration.ofSeconds(1), meters,
                provider(broken), true);

        MockServerWebExchange exchange = run(edge);

        assertThat(exchange.getAttributes().get("test.forwarded")).isEqualTo(true);
        assertThat(meters.counter("careeros.gateway.ratelimit.fallback").count()).isEqualTo(1.0);
        assertThat(meters.counter("careeros.gateway.ratelimit.refused").count()).isZero();
    }

    @Test
    void aRefusalIsJsonWithANumberToObey() {
        GatewayRateLimitFilter edge = filter(5, Duration.ofSeconds(1), stub(false), true);

        MockServerWebExchange exchange = run(edge);

        assertThat(exchange.getResponse().getStatusCode()).isEqualTo(HttpStatus.TOO_MANY_REQUESTS);
        assertThat(exchange.getResponse().getHeaders()
                .getFirst(GatewayRateLimitFilter.RETRY_AFTER)).isEqualTo("1");
    }

    @Test
    void theScriptIsOneAtomicCallWithOneKeyAndThreeArguments() {
        CapturingRedis redis = new CapturingRedis(1L);
        RedisBudget budget = new RedisBudget(redis, 3, Duration.ofSeconds(60));

        assertThat(budget.take("token:abc").block()).isTrue();

        assertThat(redis.calls).isEqualTo(1);
        assertThat(redis.keys).containsExactly(RedisBudget.KEY_PREFIX + "token:abc");
        assertThat(redis.arguments).containsExactly("3", "60000", redis.arguments[2]);
        assertThat(String.valueOf(redis.arguments[2])).matches("\\d{10,}");
        assertThat(RedisBudget.SCRIPT).contains("HGET", "HSET", "PEXPIRE", "return allowed");
        assertThat(RedisBudget.SCRIPT.split("redis.call", -1)).hasSize(5);
    }

    @Test
    void anEmptyScriptAnswerIsNotAnAdmission() {
        CapturingRedis redis = new CapturingRedis(null);
        RedisBudget budget = new RedisBudget(redis, 3, Duration.ofSeconds(60));
        assertThat(budget.take("token:abc").block()).isFalse();
    }

    @Test
    void theInProcessIdentityMapIsBounded() {
        InProcessBudget budget = new InProcessBudget(1, Duration.ofSeconds(1), 4);
        for (int i = 0; i < 40; i++) {
            budget.take("addr:10.0.0." + i).block();
        }
        assertThat(budget.size()).isLessThanOrEqualTo(5);
        assertThat(budget.flushes()).isGreaterThan(0);
    }

    // ------------------------------------------------------------------ the harness

    private static MockServerWebExchange run(GatewayRateLimitFilter edge) {
        MockServerWebExchange exchange = MockServerWebExchange.from(
                MockServerHttpRequest.get("/api/v1/health")
                        .header("Authorization", "Bearer test-token")
                        .build());
        AtomicBoolean forwarded = new AtomicBoolean();
        edge.filter(exchange, request -> {
            forwarded.set(true);
            return Mono.empty();
        }).block();
        exchange.getAttributes().put("test.forwarded", forwarded.get());
        return exchange;
    }

    private static Object field(Object target, String name) {
        try {
            java.lang.reflect.Field f = target.getClass().getDeclaredField(name);
            f.setAccessible(true);
            return f.get(target);
        } catch (ReflectiveOperationException e) {
            throw new IllegalStateException(e);
        }
    }

    /** A template that records what the budget asked it to run and answers with one value. */
    static final class CapturingRedis extends ReactiveStringRedisTemplate {
        int calls;
        List<String> keys;
        Object[] arguments;
        private final Long answer;

        CapturingRedis(Long answer) {
            super(mock(ReactiveRedisConnectionFactory.class));
            this.answer = answer;
        }

        @Override
        @SuppressWarnings("unchecked")
        public <T> Flux<T> execute(RedisScript<T> script, List<String> keys, Object... args) {
            calls++;
            this.keys = keys;
            this.arguments = args;
            return answer == null ? Flux.empty() : Flux.just((T) answer);
        }
    }
}
