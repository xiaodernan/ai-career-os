package com.careeros.common;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.UUID;
import java.util.regex.Pattern;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

/**
 * Puts one id on the answer and on every log line the answer writes.
 *
 * <p>The console pattern carries `%X{requestId}`, but nothing filled that slot: a report
 * ("the export failed at 14:03") could only be matched by guessing which of the minute's
 * requests it was. The filter runs before the security chain, so a 401 or a limiter
 * refusal carries the id too -- those are exactly the reports that arrive without a
 * session to look up.
 *
 * <p>A proxy that minted its own id may hand it in; the value is echoed only when it is
 * 8-64 characters of letters, digits, dot, dash or underscore, so a header cannot inject
 * a line break or an unbounded string into the log. Anything else is replaced by a fresh
 * UUID rather than refused: the id is diagnostics, not a credential, and a request must
 * not fail because its trace header was malformed. The id is also exposed to the browser
 * through CORS, because the contract is that a reader can quote it from a failed request
 * instead of describing the screen.
 *
 * <p>The filter also writes the access line the backend otherwise lacks: one line per
 * answer carrying the method, the request's path, the status and the elapsed time. It is
 * written under the id, so "what was happening at 14:03" is a grep of `careeros.access`
 * rather than a guess. The query string is deliberately left out -- a search term is the
 * reader's text and a reset flow carries a token, and neither belongs in every log file.
 *
 * <p>Epic 101 forwards W3C {@code traceparent}/{@code tracestate} across the mesh: a valid
 * trace is preserved and echoed; otherwise one is minted at the backend so traces remain
 * contiguous.
 */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class RequestIdFilter extends OncePerRequestFilter {

    private static final Logger accessLog = LoggerFactory.getLogger("careeros.access");

    /** The request and response header the id travels in. */
    public static final String HEADER = "X-Request-Id";

    /** W3C trace context header forwarded across the mesh (Epic 101). */
    public static final String TRACEPARENT_HEADER = "traceparent";

    /** W3C trace state header forwarded across the mesh (Epic 101). */
    public static final String TRACESTATE_HEADER = "tracestate";

    /** The MDC key `application.yml`'s console pattern reads. */
    public static final String MDC_KEY = "requestId";

    /** MDC key for W3C trace id when present (Epic 101). */
    public static final String TRACE_ID_MDC_KEY = "traceId";

    /** MDC key for the W3C traceparent header value (Epic 101). */
    public static final String TRACEPARENT_MDC_KEY = "traceparent";

    private static final Pattern ACCEPTED = Pattern.compile("[A-Za-z0-9][A-Za-z0-9._-]{7,63}");
    private static final Pattern TRACEPARENT = Pattern.compile("^[0-9a-f]{2}-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}$");

    /**
     * The id the calling thread is serving, or null when it is not serving a request --
     * a boot line, a scheduled sweep, or a pool thread between requests.
     */
    public static String currentId() {
        return MDC.get(MDC_KEY);
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
            FilterChain chain) throws ServletException, IOException {
        String inbound = request.getHeader(HEADER);
        String requestId = inbound != null && ACCEPTED.matcher(inbound).matches()
                ? inbound
                : UUID.randomUUID().toString();
        response.setHeader(HEADER, requestId);
        MDC.put(MDC_KEY, requestId);

        String inboundTrace = request.getHeader(TRACEPARENT_HEADER);
        String traceparent = (inboundTrace != null && TRACEPARENT.matcher(inboundTrace.toLowerCase()).matches())
                ? inboundTrace.toLowerCase()
                : mintTraceparent();
        String tracestate = request.getHeader(TRACESTATE_HEADER);
        response.setHeader(TRACEPARENT_HEADER, traceparent);
        MDC.put(TRACE_ID_MDC_KEY, traceId(traceparent));
        MDC.put(TRACEPARENT_MDC_KEY, traceparent);

        long startedNanos = System.nanoTime();
        try {
            chain.doFilter(request, response);
            writeAccessLine(request, response, startedNanos, traceId(traceparent));
        } catch (IOException | ServletException | RuntimeException e) {
            // The container will turn this into a 500 after the filter unwinds; a number
            // here would be one the answer does not end up carrying.
            accessLog.info("{} {} error {}ms trace={}", request.getMethod(), request.getRequestURI(),
                    elapsedMs(startedNanos), traceId(traceparent));
            throw e;
        } finally {
            // A pooled thread must not carry this request's id into the next one.
            MDC.remove(MDC_KEY);
            MDC.remove(TRACE_ID_MDC_KEY);
            MDC.remove(TRACEPARENT_MDC_KEY);
        }
    }

    private static void writeAccessLine(HttpServletRequest request, HttpServletResponse response,
            long startedNanos, String traceId) {
        accessLog.info("{} {} {} {}ms trace={}", request.getMethod(), request.getRequestURI(),
                response.getStatus(), elapsedMs(startedNanos), traceId);
    }

    private static long elapsedMs(long startedNanos) {
        return (System.nanoTime() - startedNanos) / 1_000_000;
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
}
