package com.careeros.gateway;

import java.nio.charset.StandardCharsets;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.Ordered;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

/**
 * The service-to-service surface is not a browser surface (Epic 95).
 *
 * <p>`/api/internal/**` is authenticated by a shared internal token, not by a user's
 * session, and its only caller is the backend. The edge routes every `/api/**` path, so
 * without this guard a browser could reach a surface it has no business seeing -- and a
 * token it should never need becomes a token it can try to guess. The answer is made here,
 * before the route: the backend is not called at all, so a wrong guess costs it nothing.
 *
 * <p>The refusal is a normal JSON answer rather than a dropped connection: an operator who
 * probes the edge should be told which door was closed and why, and the request id the
 * outer filter already minted travels with it.
 */
@Component
public class EdgeSurfaceGuard implements org.springframework.cloud.gateway.filter.GlobalFilter,
        Ordered {

    private static final Logger log = LoggerFactory.getLogger(EdgeSurfaceGuard.class);

    /** The prefix the backend reserves for service-to-service calls. */
    static final String INTERNAL_PREFIX = "/api/internal";

    private static final byte[] REFUSAL = ("{\"error\":\"internal-surface-not-exposed\","
            + "\"message\":\"The internal service surface is not reachable through the edge.\"}")
            .getBytes(StandardCharsets.UTF_8);

    @Override
    public Mono<Void> filter(ServerWebExchange exchange,
            org.springframework.cloud.gateway.filter.GatewayFilterChain chain) {
        String path = exchange.getRequest().getPath().value();
        if (!path.equals(INTERNAL_PREFIX) && !path.startsWith(INTERNAL_PREFIX + "/")) {
            return chain.filter(exchange);
        }
        ServerHttpResponse response = exchange.getResponse();
        response.setStatusCode(HttpStatus.FORBIDDEN);
        response.getHeaders().setContentType(MediaType.APPLICATION_JSON);
        log.info("refused internal path {} at the edge", path);
        return response.writeWith(Mono.just(response.bufferFactory().wrap(REFUSAL)));
    }

    @Override
    public int getOrder() {
        // After the request id exists, before the rate-limit bucket spends a token on a
        // call that was never going to be forwarded.
        return Ordered.HIGHEST_PRECEDENCE + 5;
    }
}
