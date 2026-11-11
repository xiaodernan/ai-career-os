package com.careeros.gateway;

import java.time.Instant;
import java.util.regex.Pattern;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;
import org.springframework.stereotype.Component;

/**
 * Stamps every /api/** request with its own deadline (Epic 128).
 *
 * <p>The edge is the one place that knows, within a few milliseconds, when a caller
 * gave up waiting -- and until this filter, nothing told the rest of the stack.
 * A browser's own timeout, a fetch aborted at 30 seconds, a queue that filled: the
 * backend and the engine kept working for a reader who had stopped waiting, and
 * every token of that work was spent on nobody.
 *
 * <p>The header is {@code X-Request-Deadline-Ms}: the epoch millisecond after which
 * the caller is gone. Policy for the value:
 *
 * <ul>
 *   <li>A well-formed caller deadline that is still in the future is kept -- the
 *       caller asked for less time than the budget, and less wins. A caller value
 *       that is past, malformed or absurd is replaced with this deployment's own
 *       budget, never forwarded as-is.</li>
 *   <li>{@code GATEWAY_DEADLINE_MS} bounds the budget (default 300000, i.e. above
 *       the 180-second AI read budget); {@code 0} or a negative value switches the
 *       stamp off entirely, for a deployment that wants the old behaviour.</li>
 *   <li>The header is stripped from the inbound request and re-set, so a caller
 *       can never pin the engine to a century -- or to one millisecond -- of
 *       budget it never granted.</li>
 * </ul>
 *
 * <p>The value crosses the mesh for information, not enforcement at the edge; the
 * backend's AI bridge consults it before dispatch and refuses work whose budget
 * already passed (Epic 128, enforced there and at the engine's boundary).
 */
@Component
public class DeadlineHeaderFilter implements GlobalFilter, Ordered {

    private static final Logger log = LoggerFactory.getLogger(DeadlineHeaderFilter.class);

    /** The header the rest of the mesh reads. */
    public static final String HEADER = "X-Request-Deadline-Ms";

    private static final Pattern ACCEPTED = Pattern.compile("\\d{1,15}");

    private final long budgetMillis;

    public DeadlineHeaderFilter(@Value("${GATEWAY_DEADLINE_MS:300000}") long budgetMillis) {
        this.budgetMillis = budgetMillis;
    }

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        if (budgetMillis <= 0 || !isApiRoute(exchange.getRequest().getPath().value())) {
            return chain.filter(exchange);
        }
        long now = Instant.now().toEpochMilli();
        Long inbound = parseInbound(exchange.getRequest().getHeaders().getFirst(HEADER), now);
        long deadline = inbound != null ? inbound : now + budgetMillis;

        ServerWebExchange stamped = exchange.mutate()
                .request(r -> r.headers(headers -> {
                    headers.remove(HEADER);
                    headers.set(HEADER, String.valueOf(deadline));
                }))
                .build();
        return chain.filter(stamped);
    }

    private static boolean isApiRoute(String path) {
        return path.startsWith("/api/");
    }

    /** The caller's deadline when it is well-formed and still in the future. */
    private static Long parseInbound(String raw, long now) {
        if (raw == null) {
            return null;
        }
        String trimmed = raw.trim();
        if (!ACCEPTED.matcher(trimmed).matches()) {
            return null;
        }
        try {
            long parsed = Long.parseLong(trimmed);
            return parsed > now ? parsed : null;
        } catch (NumberFormatException e) {
            return null;
        }
    }

    @Override
    public int getOrder() {
        // Before the rate limiter spends a token and before route resolution does any
        // work: the budget is a precondition, not an outcome. +5 keeps the request-id
        // mint (whatever it is set to today) ahead of us and the limiter at +10 behind.
        return Ordered.HIGHEST_PRECEDENCE + 5;
    }
}
