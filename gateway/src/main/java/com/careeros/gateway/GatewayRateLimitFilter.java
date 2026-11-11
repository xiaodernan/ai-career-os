package com.careeros.gateway;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Duration;
import java.util.HexFormat;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

/**
 * A caller who asks too fast gets a number they can obey (Epic 89.2, shared in 120).
 *
 * <p>The budget is per identity rather than per process: an authenticated caller is
 * known by a hash of their bearer token (the raw credential is never kept as a map key),
 * and an anonymous caller by the address the socket actually came from. One noisy
 * browser or script therefore cannot spend another reader's allowance, and a NAT full of
 * legitimate users is the one case where they share -- which is the same trade every
 * address-based limiter makes.
 *
 * <p><b>Where the budget lives</b> is the operator's choice. By default it is this
 * process's map of token buckets, correct for one replica and wrong for three: the
 * production overlay scales the edge, and three replicas each enforcing the configured
 * allowance admit three times it. {@code GATEWAY_RATE_LIMIT_REDIS=true} moves the
 * decision into Redis, where one script is one atomic read-refill-take and every replica
 * spends from the same bucket. Redis being unreachable neither opens the door nor closes
 * it: the filter falls back to this process's budget, counts the fallback and says so in
 * the log, because an edge that refuses every caller during a cache outage is an outage
 * of its own.
 *
 * <p>The refusal is JSON with {@code Retry-After: 60} (or the configured period, rounded
 * up to a whole second). A 429 with a number is actionable; a timeout is not.
 */
@Component
public class GatewayRateLimitFilter implements GlobalFilter, Ordered {

    /** The header that tells a caller when asking again may work. */
    public static final String RETRY_AFTER = HttpHeaders.RETRY_AFTER;

    private static final Logger log = LoggerFactory.getLogger(GatewayRateLimitFilter.class);

    private final int tokensPerPeriod;
    private final String retryAfter;
    private final EdgeBudget local;
    private final EdgeBudget shared;
    private final boolean distributed;
    private final Counter refusals;
    private final Counter fallbacks;

    /** The pre-Epic-120 shape, kept so a unit test can build the single-replica edge. */
    public GatewayRateLimitFilter(int tokensPerPeriod, Duration period, MeterRegistry meterRegistry) {
        this(tokensPerPeriod, period, meterRegistry, null, false);
    }

    @Autowired
    public GatewayRateLimitFilter(
            @Value("${GATEWAY_RATE_LIMIT_PER_MINUTE:1200}") int tokensPerPeriod,
            @Value("${GATEWAY_RATE_LIMIT_PERIOD:60s}") Duration period,
            MeterRegistry meterRegistry,
            ObjectProvider<EdgeBudget> sharedBudget,
            @Value("${GATEWAY_RATE_LIMIT_REDIS:false}") boolean distributed) {        this.tokensPerPeriod = tokensPerPeriod;
        this.retryAfter = String.valueOf(Math.max(1, period.toSeconds()));
        this.local = new InProcessBudget(tokensPerPeriod, period);
        this.shared = sharedBudget == null ? null : sharedBudget.getIfAvailable();
        this.distributed = distributed && this.shared != null;
        // No identity tag: the identity is a caller's token hash or address, and a metric
        // tagged by either grows one series per caller -- the cardinality accident that
        // makes a metrics backend fall over precisely during the flood this counter exists
        // to describe. The name carries the project's `careeros.` namespace like every
        // other meter the fleet registers: the alarm gate's roster walks the services that
        // consult MeterRegistry, and a meter outside the namespace is a series no rule
        // there can watch.
        this.refusals = Counter.builder("careeros.gateway.ratelimit.refused")
                .description("Requests refused by the edge token bucket")
                .register(meterRegistry);
        this.fallbacks = Counter.builder("careeros.gateway.ratelimit.fallback")
                .description("Rate-limit decisions answered locally because the shared budget failed")
                .register(meterRegistry);
    }

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        if (tokensPerPeriod <= 0) {
            return chain.filter(exchange);
        }
        String identity = identity(exchange.getRequest());
        EdgeBudget budget = distributed ? shared : local;
        return budget.take(identity)
                .onErrorResume(error -> {
                    // The shared budget is a dependency of the *decision*, not of the
                    // request. Losing it costs the caller only the guarantee that the
                    // fleet's allowance is shared for as long as the outage lasts.
                    fallbacks.increment();
                    log.warn("edge budget {} failed ({}); answering from {}",
                            budget.name(), error.toString(), local.name());
                    return local.take(identity);
                })
                .flatMap(allowed -> allowed ? chain.filter(exchange) : refuse(exchange.getResponse()));
    }

    private Mono<Void> refuse(ServerHttpResponse response) {
        refusals.increment();
        response.setStatusCode(HttpStatus.TOO_MANY_REQUESTS);
        response.getHeaders().setContentType(MediaType.APPLICATION_JSON);
        response.getHeaders().set(RETRY_AFTER, retryAfter);
        byte[] body = ("{\"error\":\"rate-limited\",\"message\":\"Too many requests; "
                + "try again shortly.\"}").getBytes(StandardCharsets.UTF_8);
        return response.writeWith(Mono.just(response.bufferFactory().wrap(body)));
    }

    private static String identity(ServerHttpRequest request) {
        String authorization = request.getHeaders().getFirst(HttpHeaders.AUTHORIZATION);
        if (authorization != null && !authorization.isBlank()) {
            return "token:" + digest(authorization);
        }
        InetSocketAddress remote = request.getRemoteAddress();
        return "addr:" + (remote == null || remote.getAddress() == null
                ? "unknown"
                : remote.getAddress().getHostAddress());
    }

    private static String digest(String credential) {
        try {
            MessageDigest sha256 = MessageDigest.getInstance("SHA-256");
            byte[] hash = sha256.digest(credential.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(hash, 0, 8);
        } catch (NoSuchAlgorithmException impossible) {
            throw new IllegalStateException("SHA-256 is part of every JDK", impossible);
        }
    }

    /** Which budget answers the next decision; asserted by the fallback test. */
    String budgetInUse() {
        return distributed ? shared.name() : local.name();
    }

    EdgeBudget localBudget() {
        return local;
    }

    @Override
    public int getOrder() {
        // After the request id is minted, before any routing or rewriting happens.
        return Ordered.HIGHEST_PRECEDENCE + 10;
    }
}
