package com.careeros.ratelimit;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;

import com.careeros.auth.dto.LoginRequest;
import com.careeros.auth.service.AuthService;
import com.careeros.auth.web.AuthController;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.common.EnvelopeAdvice;
import com.careeros.common.GlobalExceptionHandler;
import com.careeros.config.AppProperties;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

/**
 * Epic 447 — a credential-stuffing burst against the sign-in door, in process.
 *
 * The stack-level stuffing run (11,052 requests) is a real measurement but needs a
 * live stack; a harness sandbox cannot reach its loopback. This gate drives the SAME
 * path — filter -> limiter -> controller — with no socket, no Redis and no Docker.
 * The fake template models the Lua script atomically (one lock, unique ZSET members)
 * and every request is a wrong password, so the only question the numbers answer is
 * whether the per-IP ceiling holds under a simultaneous crowd.
 *
 * What it proves: the ceiling admits exactly its configured number of attempts, the
 * rest are refused before any auth work happens, no wrong password ever succeeds,
 * nothing answers 5xx, and a different IP is not caught in the same bucket.
 */
class AuthLoginCredentialStuffingTest {

    private static final int CALLERS = 200;
    private static final int THREADS = 16;
    private static final String BODY =
            "{\"email\":\"victim@example.invalid\",\"password\":\"wrong-password\"}";

    @Test
    void twoHundredSimultaneousWrongPasswordsAreCappedAtThePerIpCeiling() throws Exception {
        AppProperties props = new AppProperties();
        // With trust on, the attacker's IP travels in the header the real edge sets.
        props.getHttp().setTrustForwardedFor(true);
        int ceiling = props.getRatelimit().getAuthPerMinute();
        String attackerIp = "203.0.113.7";
        String bystanderIp = "198.51.100.9";

        RedisSlidingWindowRateLimiter limiter = new RedisSlidingWindowRateLimiter(
                new RedisSlidingWindowConcurrencyTest.AtomicScriptRedis());
        SimpleMeterRegistry meters = new SimpleMeterRegistry();
        RateLimitFilter filter = new RateLimitFilter(props, limiter, new ObjectMapper(),
                new RateLimitMetrics(meters));

        AuthService auth = mock(AuthService.class);
        doThrow(new ApiException(ApiErrorCode.INVALID_CREDENTIALS, "Invalid email or password"))
                .when(auth).login(any(LoginRequest.class));
        AuthController controller = new AuthController(auth, mock(com.careeros.auth.service.TokenService.class),
                mock(com.careeros.auth.service.EmailChangeService.class), props);
        MockMvc mvc = MockMvcBuilders.standaloneSetup(controller)
                .setControllerAdvice(new EnvelopeAdvice(), new GlobalExceptionHandler())
                .addFilters(filter)
                .build();

        AtomicInteger admitted = new AtomicInteger();
        AtomicInteger refused = new AtomicInteger();
        AtomicInteger serverErrors = new AtomicInteger();
        CountDownLatch start = new CountDownLatch(1);
        ExecutorService pool = Executors.newFixedThreadPool(THREADS);
        try {
            List<Future<?>> futures = new java.util.ArrayList<>();
            for (int i = 0; i < CALLERS; i += 1) {
                futures.add(pool.submit(() -> {
                    start.await();
                    int status = status(mvc, attackerIp);
                    if (status == 401) admitted.incrementAndGet();
                    else if (status == 429) refused.incrementAndGet();
                    else if (status >= 500) serverErrors.incrementAndGet();
                    return null;
                }));
            }
            start.countDown();
            for (Future<?> future : futures) {
                future.get(30, TimeUnit.SECONDS);
            }
        } finally {
            pool.shutdownNow();
        }

        assertThat(admitted.get())
                .as("exactly the ceiling's worth of wrong passwords reach the password check")
                .isEqualTo(ceiling);
        assertThat(refused.get())
                .as("every other attempt is refused by the filter")
                .isEqualTo(CALLERS - ceiling);
        assertThat(serverErrors.get()).as("a crowd of bad logins must never produce a 5xx").isZero();
        verify(auth, times(ceiling)).login(any(LoginRequest.class));

        // The ceiling is per IP, not a global lockout: a different source is still
        // allowed to reach the password check (and is refused there, not by the filter).
        assertThat(status(mvc, bystanderIp)).isEqualTo(401);

        double denied = meters.find(RateLimitMetrics.DECISIONS)
                .tag("bucket", RateLimitFilter.AUTH)
                .tag("outcome", RateLimitMetrics.DENIED)
                .counter().count();
        assertThat(denied).isEqualTo(CALLERS - ceiling);
    }

    private static int status(MockMvc mvc, String ip) throws Exception {
        return mvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders
                        .post("/api/v1/auth/login")
                        .header("X-Forwarded-For", ip)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(BODY))
                .andReturn().getResponse().getStatus();
    }
}
