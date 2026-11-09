package com.careeros.gateway;

import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.http.HttpHeaders;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

/**
 * Every answer leaves with the headers that keep a browser from reinterpreting it (Epic 97).
 *
 * <p>These are set before the chain runs, not after it, because the answers that need them
 * most are the short ones: the 403 from the internal-surface guard, the 429 from the token
 * bucket, the 413 from the size cap. A filter that decorates only successful responses
 * would leave exactly the error pages a browser is most likely to display unguarded.
 *
 * <p>`nosniff` stops a JSON refusal from being treated as HTML, `DENY` stops an API answer
 * from being framed, and `no-referrer` keeps a URL out of the next origin's logs. HSTS is
 * deliberately absent: the edge may terminate plain HTTP behind a proxy, and a header that
 * only means something over TLS belongs to the layer that owns TLS.
 */
@Component
public class EdgeSecurityHeadersFilter implements GlobalFilter, Ordered {

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        HttpHeaders headers = exchange.getResponse().getHeaders();
        headers.set("X-Content-Type-Options", "nosniff");
        headers.set("X-Frame-Options", "DENY");
        headers.set("Referrer-Policy", "no-referrer");
        return chain.filter(exchange);
    }

    @Override
    public int getOrder() {
        // The request id is minted first; everything after this one -- guard, limiter,
        // route -- can answer early and still carry the headers.
        return Ordered.HIGHEST_PRECEDENCE + 1;
    }
}
