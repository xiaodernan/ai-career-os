package com.careeros.ratelimit;

import com.careeros.common.ApiError;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiResponse;
import com.careeros.common.AuthUser;
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
 * Registered as a plain filter inside the security chain (see SecurityConfig) and toggled by
 * app.ratelimit.enabled. Over-limit requests receive HTTP 429 with the standard envelope, code RATE_LIMITED.
 *
 * <p>What counts as AI-costing is broader than the `/api/v1/ai/**` streaming routes. Every path
 * in {@link #isAiCost} spends provider tokens or money, and the most expensive one — the copilot
 * agent turn, which can run up to eight model calls plus tool work — is not under `/ai` at all.
 * Limiting only `/ai` therefore left the costly endpoints effectively unthrottled. Read-only
 * routes (job search, dashboards, listing) are deliberately excluded so normal browsing is not
 * rate-limited.
 */
public class RateLimitFilter extends org.springframework.web.filter.OncePerRequestFilter {

    private final AppProperties props;
    private final RedisSlidingWindowRateLimiter limiter;
    private final ObjectMapper objectMapper;

    public RateLimitFilter(AppProperties props, RedisSlidingWindowRateLimiter limiter, ObjectMapper objectMapper) {
        this.props = props;
        this.limiter = limiter;
        this.objectMapper = objectMapper;
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        return !props.getRatelimit().isEnabled() || ruleFor(request.getRequestURI()) == null;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        String uri = request.getRequestURI();
        boolean ai = !uri.startsWith("/api/v1/auth");
        int limit = ai ? props.getRatelimit().getAiPerMinute() : props.getRatelimit().getAuthPerMinute();
        String identity = ai ? userOrIp(request) : clientIp(request);
        String key = "ratelimit:" + (ai ? "ai:" : "auth:") + identity;

        if (!limiter.tryAcquire(key, limit, Duration.ofMinutes(1))) {
            response.setStatus(429);
            response.setHeader("Retry-After", "60");
            response.setContentType(MediaType.APPLICATION_JSON_VALUE);
            ApiResponse<Void> body = ApiResponse.error(
                    ApiError.of(ApiErrorCode.RATE_LIMITED, "Too many requests, slow down"));
            objectMapper.writeValue(response.getOutputStream(), body);
            return;
        }
        chain.doFilter(request, response);
    }

    /** The bucket for a URI, or null when the path is not limited. Package-private for tests. */
    static String ruleFor(String uri) {
        if (uri.startsWith("/api/v1/auth")) {
            return "auth";
        }
        return isAiCost(uri) ? "ai" : null;
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
                || uri.startsWith("/api/v1/knowledge/text")) { // embedding ingest
            return true;
        }
        // Sub-paths that trigger AI on an otherwise cheap resource.
        return uri.matches("^/api/v1/resumes/[^/]+/parse/?$")
                || uri.matches("^/api/v1/jobs/[^/]+/(match|tailor|cover-letter)/?$");
    }

    private static String userOrIp(HttpServletRequest request) {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth != null && auth.getPrincipal() instanceof AuthUser user) {
            return user.id().toString();
        }
        return clientIp(request);
    }

    /** Deployments sit behind a trusted reverse proxy that sets X-Forwarded-For; direct clients cannot spoof it there. */
    static String clientIp(HttpServletRequest request) {
        String forwarded = request.getHeader("X-Forwarded-For");
        if (forwarded != null && !forwarded.isBlank()) {
            return forwarded.split(",")[0].trim();
        }
        return request.getRemoteAddr();
    }
}
