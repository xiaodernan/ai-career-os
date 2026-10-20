package com.careeros.ratelimit;

import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import com.careeros.config.AppProperties;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Rate-limit status (16.2): the current rate-limit configuration and the caller's
 * current bucket usage. Read-only, user-scoped.
 *
 * <p>Only the *AI* bucket is reported per user: it is keyed by the authenticated
 * user id, so the number the page shows is the number the limiter enforces. The
 * auth bucket is keyed by client IP, which the server cannot know from the
 * principal alone — reporting a number for it here would be a guess, and a
 * wrong quota is worse than no quota.
 */
@RestController
@RequestMapping("/api/v1/rate-limit")
public class RateLimitController {

    private final AppProperties props;
    private final RedisSlidingWindowRateLimiter limiter;

    public RateLimitController(AppProperties props, RedisSlidingWindowRateLimiter limiter) {
        this.props = props;
        this.limiter = limiter;
    }

    /**
     * The caller's current rate-limit status: the configured limits and the
     * remaining tokens in the AI bucket.
     */
    @GetMapping("/status")
    public Map<String, Object> status(@CurrentUser AuthUser user) {
        int aiLimit = props.getRatelimit().getAiPerMinute();
        return Map.of(
                "enabled", props.getRatelimit().isEnabled(),
                "aiPerMinute", aiLimit,
                "authPerMinute", props.getRatelimit().getAuthPerMinute(),
                "aiRemaining", limiter.remaining("ratelimit:ai:" + user.id(), aiLimit));
    }
}
