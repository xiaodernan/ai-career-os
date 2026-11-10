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
 *
 * <p>Epic 101 adds W3C {@code traceparent} propagation across the edge. A valid trace
 * context is forwarded to the downstream services; otherwise a fresh one is minted at the
 * gateway so the whole request chain shares one trace id.
 */
@Component
public class RequestIdFilter implements GlobalFilter, Ordered {

    /** The request and response header the id travels in. */
    public static final String HEADER = "X-Request-Id";

    /** W3C trace context header forwarded across the mesh (Epic 101). */
    public static final String TRACEPARENT_HEADER = "traceparent";

    /** W3C trace state header forwarded across the mesh (Epic 101). */
    public static final String TRACESTATE_HEADER = "tracestate";

    /** The MDC key the gateway's console pattern reads. */
    public static final String MDC_KEY = "requestId";

    private static final Logger log = LoggerFactory.getLogger("careeros.gateway.access");

    private static final Pattern ACCEPTED = Pattern.compile("[A-Za-z0-9][A-Za-z0-9._-]{7,63}");
    // W3C traceparent: version(2)-trace-id(32)-parent-id/span-id(16)-trace-flags(2)
    private static final Pattern TRACEPARENT = Pattern.compile("^[0-9a-f]{2}-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}$");

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String inbound = exchange.getRequest().getHeaders().getFirst(HEADER);
        String requestId = inbound != null && ACCEPTED.matcher(inbound).matches()
                ? inbound
                : UUID.randomUUID().toString();

        String inboundTrace = exchange.getRequest().getHeaders().getFirst(TRACEPARENT_HEADER);
        String traceparent = (inboundTrace != null && TRACEPARENT.matcher(inboundTrace.toLowerCase()).matches())
                ? inboundTrace.toLowerCase()
                : mintTraceparent();

        String tracestate = exchange.getRequest().getHeaders().getFirst(TRACESTATE_HEADER);

        ServerHttpRequest.Builder builder = exchange.getRequest().mutate()
                .headers(headers -> {
                    headers.set(HEADER, requestId);
                    headers.set(TRACEPARENT_HEADER, traceparent);
                    if (tracestate != null && !tracestate.isBlank()) {
                        headers.set(TRACESTATE_HEADER, tracestate);
                    }
                });
        ServerHttpRequest request = builder.build();
        exchange.getResponse().getHeaders().set(HEADER, requestId);
        exchange.getResponse().getHeaders().set(TRACEPARENT_HEADER, traceparent);
        long startedNanos = System.nanoTime();
        return chain.filter(exchange.mutate().request(request).build())
                .doOnEach(signal -> {
                    // doOnEach runs for every signal; the complete/error ones are the
                    // answer being written, and the access line belongs exactly there.
                    if (signal.isOnComplete() || signal.isOnError()) {
                        MDC.put(MDC_KEY, requestId);
                        try {
                            log.info("{} {} {} {}ms trace={}", exchange.getRequest().getMethod(),
                                    exchange.getRequest().getURI().getRawPath(),
                                    exchange.getResponse().getStatusCode(),
                                    (System.nanoTime() - startedNanos) / 1_000_000,
                                    traceId(traceparent));
                        } finally {
                            MDC.remove(MDC_KEY);
                        }
                    }
                });
    }

    private static String mintTraceparent() {
        return "00-" + randomHex(32) + "-" + randomHex(16) + "-01";
    }

    private static String randomHex(int len) {
        java.security.SecureRandom random = new java.security.SecureRandom();
        byte[] bytes = new byte[len / 2];
        random.nextBytes(bytes);
        StringBuilder out = new StringBuilder(len);
        for (byte b : bytes) {
            out.append(String.format("%02x", b & 0xff));
        }
        return out.toString();
    }

    private static String traceId(String traceparent) {
        if (traceparent == null) {
            return "-";
        }
        String[] parts = traceparent.split("-");
        return parts.length >= 2 ? parts[1] : "-";
    }

    @Override
    public int getOrder() {
        return Ordered.HIGHEST_PRECEDENCE;
    }
}
