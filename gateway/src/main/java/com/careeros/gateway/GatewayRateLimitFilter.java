package com.careeros.gateway;

import io.github.resilience4j.ratelimiter.RateLimiter;
import io.github.resilience4j.ratelimiter.RateLimiterConfig;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Duration;
import java.util.HexFormat;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
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
 * A caller who asks too fast gets a number they can obey (Epic 89.2).
 *
 * <p>The budget is per identity rather than per process: an authenticated caller is
 * known by a hash of their bearer token (the raw credential is never kept as a map key),
 * and an anonymous caller by the address the socket actually came from. One noisy
 * browser or script therefore cannot spend another reader's allowance, and a NAT full of
 * legitimate users is the one case where they share -- which is the same trade every
 * address-based limiter makes.
 *
 * <p>The limiter is Resilience4j's, already present for the circuit, configured as a
 * token bucket: {@code GATEWAY_RATE_LIMIT_PER_MINUTE} tokens refreshed over
 * {@code GATEWAY_RATE_LIMIT_PERIOD}, no waiting. Zero disables the filter, which is the
 * escape hatch an operator needs when the edge is not the bottleneck.
 *
 * <p>The refusal is JSON with {@code Retry-After: 60} (or the configured period, rounded
 * up to a whole second). A 429 with a number is actionable; a timeout is not.
 */
@Component
public class GatewayRateLimitFilter implements GlobalFilter, Ordered {

    /** The header that tells a caller when asking again may work. */
    public static final String RETRY_AFTER = HttpHeaders.RETRY_AFTER;

    private final int tokensPerPeriod;
    private final Duration period;
    private final String retryAfter;
    private final Map<String, RateLimiter> limiters = new ConcurrentHashMap<>();

    public GatewayRateLimitFilter(
            @Value("${GATEWAY_RATE_LIMIT_PER_MINUTE:1200}") int tokensPerPeriod,
            @Value("${GATEWAY_RATE_LIMIT_PERIOD:60s}") Duration period) {
        this.tokensPerPeriod = tokensPerPeriod;
        this.period = period;
        this.retryAfter = String.valueOf(Math.max(1, period.toSeconds()));
    }

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        if (tokensPerPeriod <= 0) {
            return chain.filter(exchange);
        }
        RateLimiter limiter = limiters.computeIfAbsent(identity(exchange.getRequest()),
                key -> RateLimiter.of("edge", RateLimiterConfig.custom()
                        .limitForPeriod(tokensPerPeriod)
                        .limitRefreshPeriod(period)
                        .timeoutDuration(Duration.ZERO)
                        .build()));
        if (limiter.acquirePermission()) {
            return chain.filter(exchange);
        }
        return refuse(exchange.getResponse());
    }

    private Mono<Void> refuse(ServerHttpResponse response) {
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

    @Override
    public int getOrder() {
        // After the request id is minted, before any routing or rewriting happens.
        return Ordered.HIGHEST_PRECEDENCE + 10;
    }
}
