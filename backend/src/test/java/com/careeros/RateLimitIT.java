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
import org.springframework.test.web.servlet.MvcResult;

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
    void addressMoveMailsFiveTimesPerMinuteThenReturns429() throws Exception {
        // The letter relay is metered per account: every call mails a confirmation and a
        // warning, so the sixth move in a minute is refused rather than mailed.
        String email = "rl-move-" + UUID.randomUUID() + "@example.com";
        MvcResult registration = mvc.perform(post("/api/v1/auth/register")
                        .header("X-Forwarded-For", "10.88.5.11")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(JSON.writeValueAsString(Map.of(
                                "email", email,
                                "password", "Str0ngPassphrase!23",
                                "displayName", "Relay Tester"))))
                .andExpect(status().isCreated())
                .andReturn();
        String token = JSON.readTree(registration.getResponse().getContentAsString())
                .path("data").path("tokens").path("accessToken").asText();
        String move = JSON.writeValueAsString(Map.of(
                "password", "Str0ngPassphrase!23",
                "newEmail", "rl-moved-" + UUID.randomUUID() + "@example.com"));
        for (int i = 1; i <= 5; i++) {
            mvc.perform(post("/api/v1/me/email-change").header("Authorization", "Bearer " + token)
                            .contentType(MediaType.APPLICATION_JSON).content(move))
                    .andExpect(status().isOk());
        }
        mvc.perform(post("/api/v1/me/email-change").header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON).content(move))
                .andExpect(status().isTooManyRequests())
                .andExpect(jsonPath("$.error.code").value("RATE_LIMITED"));
    }

    @Test
    void mfaActivationJudgesFiveCodesPerAccountThenReturns429() throws Exception {
        // A six-digit code is a million possibilities, so the meter is the account's, not the
        // address's: five verdicts in a minute, then the sixth answer is the limiter's.
        String email = "rl-mfa-" + UUID.randomUUID() + "@example.com";
        MvcResult registration = mvc.perform(post("/api/v1/auth/register")
                        .header("X-Forwarded-For", "10.88.6.12")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(JSON.writeValueAsString(Map.of(
                                "email", email,
                                "password", "Str0ngPassphrase!23",
                                "displayName", "Factor Tester"))))
                .andExpect(status().isCreated())
                .andReturn();
        String token = JSON.readTree(registration.getResponse().getContentAsString())
                .path("data").path("tokens").path("accessToken").asText();
        String proof = JSON.writeValueAsString(Map.of(
                "password", "Str0ngPassphrase!23",
                "code", "000000"));
        for (int i = 1; i <= 5; i++) {
            // No enrollment exists, so the code is judged and refused -- but it was judged,
            // which is the work the ceiling meters.
            mvc.perform(post("/api/v1/me/mfa/activate").header("Authorization", "Bearer " + token)
                            .contentType(MediaType.APPLICATION_JSON).content(proof))
                    .andExpect(status().isBadRequest());
        }
        mvc.perform(post("/api/v1/me/mfa/activate").header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON).content(proof))
                .andExpect(status().isTooManyRequests())
                .andExpect(jsonPath("$.error.code").value("RATE_LIMITED"));

        // Reprint and disable judge a code too, so they share the account's bucket: once it is
        // spent, the newer doors are shut for the same minute.
        for (String path : java.util.List.of("/api/v1/me/mfa/recovery-codes",
                "/api/v1/me/mfa/disable")) {
            mvc.perform(post(path).header("Authorization", "Bearer " + token)
                            .contentType(MediaType.APPLICATION_JSON).content(proof))
                    .andExpect(status().isTooManyRequests());
        }
        // The status read is not a code judgement, so the settings card still gets its answer.
        mvc.perform(get("/api/v1/me/mfa").header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.enabled").value(false));
    }

    @Test
    void theInboundWebhookIsMeteredPerAddressThenReturns429() throws Exception {
        // Every account's deliveries arrive from the provider's own hosts, so the meter is the
        // address's: ten letters for one token in a minute, then the eleventh is the limiter's.
        String token = "fake." + UUID.randomUUID().toString().replace("-", "");
        String body = JSON.writeValueAsString(Map.of(
                "MessageID", UUID.randomUUID().toString(),
                "From", "recruiter@example.com",
                "Subject", "Your application",
                "TextBody", "Hello"));
        for (int i = 1; i <= 10; i++) {
            // The token decodes to no account, so the service answers 404 -- but only after the
            // limiter admitted the delivery, which is the work the ceiling meters.
            mvc.perform(post("/api/v1/inbound/mail/" + token)
                            .contentType(MediaType.APPLICATION_JSON).content(body))
                    .andExpect(status().isNotFound());
        }
        mvc.perform(post("/api/v1/inbound/mail/" + token)
                        .contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isTooManyRequests())
                .andExpect(jsonPath("$.error.code").value("RATE_LIMITED"));

        // Another address keeps its own window.
        mvc.perform(post("/api/v1/inbound/mail/other." + token)
                        .contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isNotFound());
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
