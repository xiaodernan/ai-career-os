package com.careeros.gateway;

import java.nio.charset.StandardCharsets;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.Ordered;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

/**
 * Optional shared-secret gate for the edge's operations surface (Epic 108.15).
 *
 * <p>The gateway's actuator endpoints (`/actuator/info`, `/actuator/gateway/routes`,
 * `/actuator/metrics`, `/actuator/circuitbreakers`, ...) are served by this process. On a
 * default `docker compose up` nothing protects them: compose binds the port to loopback,
 * which keeps a guest network out, and a production reverse proxy is expected to
 * authenticate what it proxies. That is fine until the edge is published somewhere the
 * proxy does not look.
 *
 * <p>`GATEWAY_ACTUATOR_TOKEN` closes that gap without touching the deploy: set it and every
 * `/actuator/**` request must carry the `X-Actuator-Token` header with the same value,
 * otherwise the edge answers 403 and the actuator is never reached. The container probe
 * (`/actuator/health`) is always allowed — orchestrators never see a secret — and every
 * route is otherwise unchanged. When the knob is unset the surface stays open, exactly as
 * before, so existing deployments and dev flows do not regress.
 *
 * <p>These endpoints answer directly from the web context rather than through a gateway
 * route, so this guard runs as a {@link org.springframework.web.server.WebFilter} ahead of
 * every handler — not only on routed requests. The {@link #filter(ServerWebExchange, org.springframework.cloud.gateway.filter.GatewayFilterChain)}
 * twin exists so gateway exchanges also refuse before spending a rate-limit token or
 * routing a browser that never had the field to fill in.
 */
@Component
public class GatewayActuatorGuard implements org.springframework.web.server.WebFilter,
        org.springframework.cloud.gateway.filter.GlobalFilter,
        Ordered {

    private static final Logger log = LoggerFactory.getLogger(GatewayActuatorGuard.class);

    /** The path that must stay open for the container probe; nothing else. */
    private static final String HEALTH = "/actuator/health";
    private static final String PREFIX = "/actuator";

    private static final byte[] REFUSAL = ("{\"error\":\"actuator-surface-not-exposed\","
            + "\"message\":\"The operations surface is not exposed.\"}")
            .getBytes(StandardCharsets.UTF_8);

    private final String actuatorToken;

    public GatewayActuatorGuard(@Value("${GATEWAY_ACTUATOR_TOKEN:}") String actuatorToken) {
        this.actuatorToken = actuatorToken == null ? "" : actuatorToken.trim();
    }

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, org.springframework.web.server.WebFilterChain chain) {
        Decision decision = decide(exchange);
        if (decision == Decision.REFUSE) {
            return refuse(exchange);
        }
        return chain.filter(exchange);
    }

    @Override
    public Mono<Void> filter(ServerWebExchange exchange,
            org.springframework.cloud.gateway.filter.GatewayFilterChain chain) {
        Decision decision = decide(exchange);
        if (decision == Decision.REFUSE) {
            return refuse(exchange);
        }
        return chain.filter(exchange);
    }

    private Decision decide(ServerWebExchange exchange) {
        String path = exchange.getRequest().getPath().value();
        if (actuatorToken.isBlank()
                || !path.equals(PREFIX) && !path.startsWith(PREFIX + "/")
                || path.equals(HEALTH)) {
            return Decision.PASS;
        }
        String presented = exchange.getRequest().getHeaders().getFirst("X-Actuator-Token");
        return actuatorToken.equals(presented) ? Decision.PASS : Decision.REFUSE;
    }

    private Mono<Void> refuse(ServerWebExchange exchange) {
        ServerHttpResponse response = exchange.getResponse();
        response.setStatusCode(HttpStatus.FORBIDDEN);
        response.getHeaders().setContentType(MediaType.APPLICATION_JSON);
        log.info("refused unauthenticated actuator path {} at the edge",
                exchange.getRequest().getPath().value());
        DataBuffer body = response.bufferFactory().wrap(REFUSAL);
        return response.writeWith(Mono.just(body));
    }

    @Override
    public int getOrder() {
        // Ahead of the route dispatch and the rate limiter: an unauthorized probe must not
        // reach the actuator nor spend a token from the bucket.
        return Ordered.HIGHEST_PRECEDENCE + 4;
    }

    private enum Decision {
        PASS,
        REFUSE
    }
}