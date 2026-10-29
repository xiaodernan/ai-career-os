package com.careeros.ratelimit;

import static org.assertj.core.api.Assertions.assertThat;

import com.careeros.common.AuthUser;
import com.careeros.config.AppProperties;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import jakarta.servlet.FilterChain;
import java.time.Duration;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;

/**
 * What the filter does with a bucket once it has one: the answer a refusal gets, the key and
 * ceiling it counted against, and the counter each decision moves. The classification itself is
 * pinned in {@link RateLimitFilterTest}; this file drives the counting method directly.
 */
class RateLimitFilterDecisionTest {

    private static final String IP = "10.0.0.7";

    private final AppProperties props = new AppProperties();
    private final SimpleMeterRegistry registry = new SimpleMeterRegistry();
    private final AtomicReference<String> countedKey = new AtomicReference<>();
    private final AtomicInteger countedLimit = new AtomicInteger();
    private final AtomicInteger countedWindowSeconds = new AtomicInteger();

    @AfterEach
    void clearContext() {
        SecurityContextHolder.clearContext();
    }

    @Test
    void aRefusalAnswersTheStandardEnvelopeAndMovesTheDeniedCounter() throws Exception {
        MockHttpServletRequest request = request("POST", "/api/v1/auth/login");
        MockHttpServletResponse response = new MockHttpServletResponse();
        AtomicBoolean chained = new AtomicBoolean();

        filter(false).doFilterInternal(request, response, chain(chained));

        assertThat(response.getStatus()).isEqualTo(429);
        assertThat(response.getHeader("Retry-After")).isEqualTo("60");
        assertThat(response.getContentAsString()).contains("RATE_LIMITED");
        assertThat(chained).isFalse();
        assertThat(count(RateLimitFilter.AUTH, RateLimitMetrics.DENIED)).isEqualTo(1.0);
        assertThat(count(RateLimitFilter.AUTH, RateLimitMetrics.ALLOWED)).isZero();
        assertThat(countedKey.get()).startsWith("ratelimit:auth:");
        assertThat(countedLimit.get()).isEqualTo(props.getRatelimit().getAuthPerMinute());
        assertThat(countedWindowSeconds.get()).isEqualTo(60);
    }

    @Test
    void anAdmittedAiRequestRunsTheChainAndIsKeyedByTheAccount() throws Exception {
        UUID userId = signIn();
        MockHttpServletRequest request = request("GET", "/api/v1/jobs/abc/match");
        MockHttpServletResponse response = new MockHttpServletResponse();
        AtomicBoolean chained = new AtomicBoolean();

        filter(true).doFilterInternal(request, response, chain(chained));

        assertThat(chained).isTrue();
        assertThat(response.getStatus()).isEqualTo(200);
        assertThat(count(RateLimitFilter.AI, RateLimitMetrics.ALLOWED)).isEqualTo(1.0);
        assertThat(count(RateLimitFilter.AI, RateLimitMetrics.DENIED)).isZero();
        assertThat(countedKey.get()).isEqualTo("ratelimit:ai:" + userId);
        assertThat(countedLimit.get()).isEqualTo(props.getRatelimit().getAiPerMinute());
    }

    @Test
    void theMailBucketCountsAgainstItsOwnCeilingAndNotTheAiOne() throws Exception {
        UUID userId = signIn();
        MockHttpServletRequest request = request("POST", "/api/v1/me/email-change");
        MockHttpServletResponse response = new MockHttpServletResponse();
        AtomicBoolean chained = new AtomicBoolean();

        filter(false).doFilterInternal(request, response, chain(chained));

        assertThat(response.getStatus()).isEqualTo(429);
        assertThat(chained).isFalse();
        assertThat(count(RateLimitFilter.MAIL, RateLimitMetrics.DENIED)).isEqualTo(1.0);
        assertThat(count(RateLimitFilter.AI, RateLimitMetrics.DENIED)).isZero();
        assertThat(count(RateLimitFilter.AUTH, RateLimitMetrics.DENIED)).isZero();
        assertThat(countedKey.get()).isEqualTo("ratelimit:mail:" + userId);
        assertThat(countedLimit.get()).isEqualTo(props.getRatelimit().getMailPerMinute());
    }

    @Test
    void theMfaBucketCountsAgainstItsOwnCeilingAndNotTheMailOne() throws Exception {
        UUID userId = signIn();
        MockHttpServletRequest request = request("POST", "/api/v1/me/mfa/activate");
        MockHttpServletResponse response = new MockHttpServletResponse();
        AtomicBoolean chained = new AtomicBoolean();

        filter(false).doFilterInternal(request, response, chain(chained));

        assertThat(response.getStatus()).isEqualTo(429);
        assertThat(chained).isFalse();
        assertThat(count(RateLimitFilter.MFA, RateLimitMetrics.DENIED)).isEqualTo(1.0);
        assertThat(count(RateLimitFilter.MAIL, RateLimitMetrics.DENIED)).isZero();
        assertThat(count(RateLimitFilter.AI, RateLimitMetrics.DENIED)).isZero();
        // The guessed code is one account's problem, so the key names the signed-in user even
        // though the address is shared.
        assertThat(countedKey.get()).isEqualTo("ratelimit:mfa:" + userId);
        assertThat(countedLimit.get()).isEqualTo(props.getRatelimit().getMfaPerMinute());
    }

    private RateLimitFilter filter(boolean admit) {
        RedisSlidingWindowRateLimiter limiter = new RedisSlidingWindowRateLimiter(null) {
            @Override
            public boolean tryAcquire(String key, int limit, Duration window) {
                countedKey.set(key);
                countedLimit.set(limit);
                countedWindowSeconds.set((int) window.toSeconds());
                return admit;
            }
        };
        return new RateLimitFilter(props, limiter, new ObjectMapper(), new RateLimitMetrics(registry));
    }

    private static MockHttpServletRequest request(String method, String uri) {
        MockHttpServletRequest request = new MockHttpServletRequest(method, uri);
        request.setRemoteAddr(IP);
        return request;
    }

    private static FilterChain chain(AtomicBoolean chained) {
        return (request, response) -> chained.set(true);
    }

    private static UUID signIn() {
        UUID userId = UUID.randomUUID();
        SecurityContextHolder.getContext().setAuthentication(new UsernamePasswordAuthenticationToken(
                new AuthUser(userId, "reader@example.com", "USER"), null, List.of()));
        return userId;
    }

    private double count(String bucket, String outcome) {
        Counter counter = registry.find(RateLimitMetrics.DECISIONS)
                .tag("bucket", bucket)
                .tag("outcome", outcome)
                .counter();
        return counter == null ? 0.0 : counter.count();
    }
}
