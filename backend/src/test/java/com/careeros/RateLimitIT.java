package com.careeros;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.Map;
import java.util.UUID;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

class RateLimitIT extends AbstractIntegrationTest {

    private static final ObjectMapper JSON = new ObjectMapper();

    @Test
    void authEndpointAllowsTenPerMinutePerIpThenReturns429Envelope() throws Exception {
        String ip = "10.88.1.7";
        String body = JSON.writeValueAsString(Map.of("email", "rl@example.com", "password", "WrongPassw0rd!!"));
        for (int i = 1; i <= 10; i++) {
            mvc.perform(post("/api/v1/auth/login").header("X-Forwarded-For", ip)
                            .contentType(MediaType.APPLICATION_JSON).content(body))
                    .andExpect(status().isUnauthorized());
        }
        mvc.perform(post("/api/v1/auth/login").header("X-Forwarded-For", ip)
                        .contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isTooManyRequests())
                .andExpect(jsonPath("$.success").value(false))
                .andExpect(jsonPath("$.error.code").value("RATE_LIMITED"));
    }

    @Test
    void aiEndpointIsLimitedPerIdentityAndOtherIpsAreUnaffected() throws Exception {
        String crowdedIp = "10.88.2.8";
        for (int i = 1; i <= 30; i++) {
            mvc.perform(get("/api/v1/ai/stream/" + UUID.randomUUID()).header("X-Forwarded-For", crowdedIp))
                    .andExpect(status().isUnauthorized()); // no bearer token: passes limiter, denied later
        }
        mvc.perform(get("/api/v1/ai/stream/" + UUID.randomUUID()).header("X-Forwarded-For", crowdedIp))
                .andExpect(status().isTooManyRequests())
                .andExpect(jsonPath("$.error.code").value("RATE_LIMITED"));

        // A different identity keeps its own window.
        mvc.perform(get("/api/v1/ai/stream/" + UUID.randomUUID()).header("X-Forwarded-For", "10.88.3.9"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void healthReportsDbAndRedisThroughEnvelope() throws Exception {
        mvc.perform(get("/api/v1/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.status").value("ok"))
                .andExpect(jsonPath("$.data.db").value(true))
                .andExpect(jsonPath("$.data.redis").value(true));
    }
}
