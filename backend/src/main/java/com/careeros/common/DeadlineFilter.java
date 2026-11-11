package com.careeros.common;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.regex.Pattern;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

/**
 * Carries the request's own deadline across the service (Epic 128).
 *
 * <p>The edge stamps every /api/** request with {@code X-Request-Deadline-Ms} -- the
 * epoch millisecond after which the caller has stopped waiting. The deadline is not a
 * credential and not diagnostics for this service's own logs; it is the number the AI
 * bridge consults before it asks the engine to spend tokens: a request whose budget
 * already passed is refused here, in one millisecond, instead of after 180 seconds of
 * engine work nobody is listening for.
 *
 * <p>The value is echoed to the ai-service on every internal call, where it exists as a
 * backstop at the engine's own boundary. Parsing is deliberately strict -- 1 to 15
 * digits of epoch milliseconds, nothing else -- and a malformed value is ignored, not
 * refused: a deadline is work conservation, never a reason to fail a request.
 *
 * <p>A request without a deadline (the internal nightly sweep, a direct caller) behaves
 * exactly as before; the ThreadLocal is cleared in a finally so a pooled thread never
 * carries one request's budget into the next.
 */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE + 1)
public class DeadlineFilter extends OncePerRequestFilter {

    /** The header the edge stamps; forwarded to the ai-service unchanged. */
    public static final String HEADER = "X-Request-Deadline-Ms";

    /** Epoch-millisecond digits, the only accepted shape. */
    private static final Pattern ACCEPTED = Pattern.compile("\\d{1,15}");

    /** This thread's request's deadline, or null when the caller set none. */
    private static final ThreadLocal<Long> DEADLINE = new ThreadLocal<>();

    /**
     * The deadline the current request carries, or null when it carries none -- the
     * internal sweep, tests that call the bridge directly, or a caller whose value was
     * ignored. Callers must treat null as "no budget", never as "unlimited worry".
     */
    public static Long current() {
        return DEADLINE.get();
    }

    /** Whether the caller's budget for this request has already passed. */
    public static boolean expired() {
        Long deadline = DEADLINE.get();
        return deadline != null && System.currentTimeMillis() >= deadline;
    }

    /**
     * Deliberately public so the same filter drives the budget on any thread --
     * the servlet container calls it, and the test suite calls it with a mocked
     * request instead of standing up a container. Widening, not changing: the
     * container's contract is untouched.
     */
    @Override
    public void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
                                 FilterChain chain) throws ServletException, IOException {
        String inbound = request.getHeader(HEADER);
        DEADLINE.remove();
        if (inbound != null && ACCEPTED.matcher(inbound.trim()).matches()) {
            try {
                DEADLINE.set(Long.parseLong(inbound.trim()));
            } catch (NumberFormatException ignored) {
                // A 15-digit number that overflows is nonsense, not a budget; drop it.
            }
        }
        try {
            chain.doFilter(request, response);
        } finally {
            DEADLINE.remove();
        }
    }
}
