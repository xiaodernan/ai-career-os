package com.careeros.ratelimit;

import com.careeros.common.ApiError;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiResponse;
import com.careeros.common.AuthUser;
import com.careeros.common.ClientInfo;
import com.careeros.config.AppProperties;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.time.Duration;
import org.springframework.http.MediaType;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;

/**
 * Applies the Redis sliding-window limits:
 *  - /api/v1/auth/**  : per client IP, app.ratelimit.auth-per-minute (default 10/min)
 *  - AI-costing paths : per authenticated user (falls back to IP), app.ratelimit.ai-per-minute (default 30/min)
 *  - mail-sending account routes : per authenticated user (falls back to IP), app.ratelimit.mail-per-minute (default 5/min)
 * Registered as a plain filter inside the security chain (see SecurityConfig) and toggled by
 * app.ratelimit.enabled. Over-limit requests receive HTTP 429 with the standard envelope, code RATE_LIMITED.
 *
 * <p>{@link #ruleFor} is the one author of "which bucket a path lands in": {@code doFilterInternal}
 * asks it for the bucket name and reads the ceiling, the identity and the Redis key prefix off that
 * name. The earlier shape tested the auth prefix a second time to pick them, so a path could be
 * admitted by one rule and counted against another; one predicate makes that impossible.
 *
 * <p>What counts as AI-costing is broader than the `/api/v1/ai/**` streaming routes. Every path
 * in {@link #isAiCost} spends provider tokens or money, and the most expensive one — the copilot
 * agent turn, which can run up to eight model calls plus tool work — is not under `/ai` at all.
 * Limiting only `/ai` therefore left the costly endpoints effectively unthrottled. Read-only
 * routes (job search, dashboards, listing) are deliberately excluded so normal browsing is not
 * rate-limited.
 *
 * <p>The list is derived from the call sites, not from what the paths look like: every
 * {@code AiServiceClient} method that is not a status read is traced to the route that reaches
 * it, which is how the ingest and import routes joined the sub-path group below.
 *
 * <p>The mail bucket is the relay's meter: an address move mails a confirmation to the claimed
 * mailbox and a warning to the current one, so every call spends two letters. An account that can
 * call it without limit can use the product to write to any unregistered address it names.
 *
 * <p>Every decision this filter makes moves a counter tagged by the bucket that made it
 * (see {@link RateLimitMetrics}), so a ceiling refusing traffic is a reading rather than a
 * client's word for it.
 */
public class RateLimitFilter extends org.springframework.web.filter.OncePerRequestFilter {

    static final String AUTH = "auth";
    static final String AI = "ai";
    static final String MAIL = "mail";

    private final AppProperties props;
    private final RedisSlidingWindowRateLimiter limiter;
    private final ObjectMapper objectMapper;
    private final RateLimitMetrics metrics;

    public RateLimitFilter(AppProperties props, RedisSlidingWindowRateLimiter limiter, ObjectMapper objectMapper,
                           RateLimitMetrics metrics) {
        this.props = props;
        this.limiter = limiter;
        this.objectMapper = objectMapper;
        this.metrics = metrics;
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        return !props.getRatelimit().isEnabled() || ruleFor(request.getRequestURI()) == null;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        String bucket = ruleFor(request.getRequestURI());
        int limit = switch (bucket) {
            case AI -> props.getRatelimit().getAiPerMinute();
            case MAIL -> props.getRatelimit().getMailPerMinute();
            default -> props.getRatelimit().getAuthPerMinute();
        };
        String identity = AUTH.equals(bucket) ? clientIp(request) : userOrIp(request);
        String key = "ratelimit:" + bucket + ":" + identity;

        if (!limiter.tryAcquire(key, limit, Duration.ofMinutes(1))) {
            metrics.record(bucket, false);
            response.setStatus(429);
            response.setHeader("Retry-After", "60");
            response.setContentType(MediaType.APPLICATION_JSON_VALUE);
            ApiResponse<Void> body = ApiResponse.error(
                    ApiError.of(ApiErrorCode.RATE_LIMITED, "Too many requests, slow down"));
            objectMapper.writeValue(response.getOutputStream(), body);
            return;
        }
        metrics.record(bucket, true);
        chain.doFilter(request, response);
    }

    /** The bucket for a URI, or null when the path is not limited. Package-private for tests. */
    static String ruleFor(String uri) {
        if (uri.startsWith("/api/v1/auth")) {
            return AUTH;
        }
        if (sendsMail(uri)) {
            return MAIL;
        }
        return isAiCost(uri) ? AI : null;
    }

    /**
     * The signed-in routes that hand letters to the relay on every call. Both spellings of the
     * address move are listed rather than one prefix, because a route added under `/me` is not a
     * letter until someone wires it to the mail port.
     */
    static boolean sendsMail(String uri) {
        return uri.equals("/api/v1/me/email-change") || uri.equals("/api/v1/me/email-change/")
                || uri.equals("/api/v1/users/me/email-change") || uri.equals("/api/v1/users/me/email-change/");
    }

    /**
     * True for paths that invoke a model, an embedding, or the agent loop. Kept as an explicit
     * list rather than a prefix sweep so cheap reads stay unthrottled.
     */
    static boolean isAiCost(String uri) {
        if (uri.startsWith("/api/v1/ai")          // SSE streaming AI
                || uri.startsWith("/api/v1/copilot")   // agent turn (most expensive)
                || uri.startsWith("/api/v1/interview") // answer evaluation, finalize
                || uri.startsWith("/api/v1/jds")       // JD analysis + suggestions
                || uri.startsWith("/api/v1/growth")    // growth report + the granular engines behind it
                || uri.startsWith("/api/v1/knowledge/text")) { // embedding ingest
            return true;
        }
        // Sub-paths that trigger AI on an otherwise cheap resource.
        return uri.matches("^/api/v1/resumes/[^/]+/parse/?$")
                || uri.matches("^/api/v1/jobs/[^/]+/(match|tailor|cover-letter)/?$")
                // The three that spend money without living under an "AI-looking" path:
                // importing a JD runs the analyst, and both upload routes embed every chunk
                // of the document into pgvector. Left out, a scripted client could call them
                // without limit — the exact hole this list exists to close.
                || uri.matches("^/api/v1/jobs/import/?$")
                || uri.matches("^/api/v1/knowledge/documents/?$")
                || uri.matches("^/api/v1/resumes/upload/?$");
    }

    private String userOrIp(HttpServletRequest request) {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth != null && auth.getPrincipal() instanceof AuthUser user) {
            return user.id().toString();
        }
        return clientIp(request);
    }

    /**
     * X-Forwarded-For is only believed when the deployment declares a trusted proxy
     * ({@code app.http.trust-forwarded-for}); otherwise the socket's address is the
     * identity, so a direct client cannot rotate the header into fresh buckets.
     */
    private String clientIp(HttpServletRequest request) {
        return ClientInfo.clientIp(request, props.getHttp().isTrustForwardedFor());
    }
}
