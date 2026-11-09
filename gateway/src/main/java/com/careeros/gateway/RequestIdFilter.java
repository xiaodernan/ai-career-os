package com.careeros.gateway;

import java.util.UUID;
import java.util.regex.Pattern;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

/**
 * Mints or forwards the id that lets a reader quote one failing request (Epic 88).
 *
 * <p>The backend already does this on its own (its contract test requires it), but a
 * request that never reaches the backend -- a route miss, an unreachable upstream, a
 * gateway refusal -- would have no id at all. Minting at the edge means every answer
 * from every process carries the same value, and the browser sees it on the response
 * through the same CORS exposure the backend declares.
 *
 * <p>The validation rule is copied from {@code RequestIdFilter} on purpose: 8-64
 * characters starting with a letter or digit, the rest letters, digits, dot, dash or
 * underscore. Anything else is replaced rather than refused -- the header is diagnostics,
 * not a credential -- so a malformed trace header cannot fail a request.
 */
@Component
public class RequestIdFilter implements GlobalFilter, Ordered {

    /** The request and response header the id travels in. */
    public static final String HEADER = "X-Request-Id";

    /** The MDC key the gateway's console pattern reads. */
    public static final String MDC_KEY = "requestId";

    private static final Logger log = LoggerFactory.getLogger("careeros.gateway.access");

    private static final Pattern ACCEPTED = Pattern.compile("[A-Za-z0-9][A-Za-z0-9._-]{7,63}");

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String inbound = exchange.getRequest().getHeaders().getFirst(HEADER);
        String requestId = inbound != null && ACCEPTED.matcher(inbound).matches()
                ? inbound
                : UUID.randomUUID().toString();
        ServerHttpRequest request = exchange.getRequest().mutate()
                .headers(headers -> headers.set(HEADER, requestId))
                .build();
        exchange.getResponse().getHeaders().set(HEADER, requestId);
        long startedNanos = System.nanoTime();
        return chain.filter(exchange.mutate().request(request).build())
                .doOnEach(signal -> {
                    // doOnEach runs for every signal; the complete/error ones are the
                    // answer being written, and the access line belongs exactly there.
                    if (signal.isOnComplete() || signal.isOnError()) {
                        MDC.put(MDC_KEY, requestId);
                        try {
                            log.info("{} {} {} {}ms", exchange.getRequest().getMethod(),
                                    exchange.getRequest().getURI().getRawPath(),
                                    exchange.getResponse().getStatusCode(),
                                    (System.nanoTime() - startedNanos) / 1_000_000);
                        } finally {
                            MDC.remove(MDC_KEY);
                        }
                    }
                });
    }

    @Override
    public int getOrder() {
        return Ordered.HIGHEST_PRECEDENCE;
    }
}
