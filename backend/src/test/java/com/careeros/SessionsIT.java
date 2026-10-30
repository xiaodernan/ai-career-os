package com.careeros;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MvcResult;

/**
 * The session surface against the real schema (roadmap 25).
 *
 * <p>Two logins from two agents are two sessions; refreshing one of them is still that one
 * session, because rotation replaces the token without opening a new door. Closing one family
 * leaves the other able to refresh, a neighbour's family id is a 404 that closes nothing, and
 * closing all ends every refresh while the access tokens finish their short lives.
 */
class SessionsIT extends ApiIntegrationTest {

    private static final String PASSWORD = "Str0ngPassphrase!23";

    @Test
    void sessionsAreNamedListedAndClosedOneByOneOrAllAtOnce() throws Exception {
        String aliceEmail = "sessions-alice-" + UUID.randomUUID() + "@example.com";
        JsonNode aliceStart = registerWithAgent(aliceEmail, "JUnit/laptop");
        String aliceAccess = aliceStart.path("tokens").path("accessToken").asText();
        String laptopRefresh = aliceStart.path("tokens").path("refreshToken").asText();

        JsonNode phone = login(aliceEmail, "JUnit/phone");
        String phoneRefresh = phone.path("tokens").path("refreshToken").asText();

        MvcResult listed = mvc.perform(get("/api/v1/me/sessions")
                        .header("Authorization", "Bearer " + aliceAccess))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.length()").value(2))
                .andReturn();
        JsonNode sessions = body(listed);
        assertThat(agentsIn(sessions)).containsExactlyInAnyOrder("JUnit/laptop", "JUnit/phone");
        // The access token that asked was minted for the laptop's door, so that is the one
        // the list marks (38.3); the phone must not claim to be the reader's tab.
        assertThat(currentOf(sessions, "JUnit/laptop")).isTrue();
        assertThat(currentOf(sessions, "JUnit/phone")).isFalse();
        assertThat(listed.getResponse().getContentAsString())
                .doesNotContain(laptopRefresh)
                .doesNotContain(phoneRefresh);

        // Rotation replaces the token; it does not open a second door.
        MvcResult rotated = mvc.perform(post("/api/v1/auth/refresh")
                        .header("X-Forwarded-For", freshIp())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(Map.of("refreshToken", laptopRefresh))))
                .andExpect(status().isOk())
                .andReturn();
        String laptopRefresh2 = body(rotated).path("refreshToken").asText();
        mvc.perform(get("/api/v1/me/sessions").header("Authorization", "Bearer " + aliceAccess))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.length()").value(2));

        // Close the phone's door: its refresh stops, the laptop's keeps working.
        String phoneFamily = familyOf(sessions, "JUnit/phone");
        mvc.perform(delete("/api/v1/me/sessions/" + phoneFamily)
                        .header("Authorization", "Bearer " + aliceAccess))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.revoked").value(true));
        mvc.perform(post("/api/v1/auth/refresh")
                        .header("X-Forwarded-For", freshIp())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(Map.of("refreshToken", phoneRefresh))))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.error.code").value("TOKEN_REUSED"));
        String laptopRefresh3 = body(mvc.perform(post("/api/v1/auth/refresh")
                        .header("X-Forwarded-For", freshIp())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(Map.of("refreshToken", laptopRefresh2))))
                .andExpect(status().isOk())
                .andReturn()).path("refreshToken").asText();

        // A neighbour's family id is one 404, and the neighbour is still signed in.
        String bobEmail = "sessions-bob-" + UUID.randomUUID() + "@example.com";
        JsonNode bob = registerWithAgent(bobEmail, "JUnit/bob");
        String bobRefresh = bob.path("tokens").path("refreshToken").asText();
        String bobFamily = familyOf(
                body(mvc.perform(get("/api/v1/me/sessions")
                                .header("Authorization", "Bearer "
                                        + bob.path("tokens").path("accessToken").asText()))
                        .andExpect(status().isOk())
                        .andReturn()),
                "JUnit/bob");

        mvc.perform(delete("/api/v1/me/sessions/" + bobFamily)
                        .header("Authorization", "Bearer " + aliceAccess))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error.code").value("LOGIN_SESSION_NOT_FOUND"));
        mvc.perform(post("/api/v1/auth/refresh")
                        .header("X-Forwarded-For", freshIp())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(Map.of("refreshToken", bobRefresh))))
                .andExpect(status().isOk());

        // Close everything: the laptop's last successor no longer buys a pair.
        mvc.perform(delete("/api/v1/me/sessions").header("Authorization", "Bearer " + aliceAccess))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.revoked").value(true));
        mvc.perform(post("/api/v1/auth/refresh")
                        .header("X-Forwarded-For", freshIp())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(Map.of("refreshToken", laptopRefresh3))))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.error.code").value("TOKEN_REUSED"));
        mvc.perform(get("/api/v1/me/sessions").header("Authorization", "Bearer " + aliceAccess))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.length()").value(0));
    }

    private JsonNode registerWithAgent(String email, String agent) throws Exception {
        MvcResult result = mvc.perform(post("/api/v1/auth/register")
                        .header("X-Forwarded-For", freshIp())
                        .header("User-Agent", agent)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"email\":\"" + email + "\",\"password\":\"" + PASSWORD + "\","
                                + "\"displayName\":\"Session Tester\"}"))
                .andExpect(status().isCreated())
                .andReturn();
        return body(result);
    }

    private JsonNode login(String email, String agent) throws Exception {
        MvcResult result = mvc.perform(post("/api/v1/auth/login")
                        .header("X-Forwarded-For", freshIp())
                        .header("User-Agent", agent)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(Map.of("email", email, "password", PASSWORD))))
                .andExpect(status().isOk())
                .andReturn();
        return body(result);
    }

    private static JsonNode body(MvcResult result) throws Exception {
        return MAPPER.readTree(result.getResponse().getContentAsString()).path("data");
    }

    private static String familyOf(JsonNode sessions, String agent) {
        for (JsonNode session : sessions) {
            if (agent.equals(session.path("userAgent").asText())) {
                return session.path("id").asText();
            }
        }
        throw new AssertionError("no session for " + agent + " in " + sessions);
    }

    private static boolean currentOf(JsonNode sessions, String agent) {
        for (JsonNode session : sessions) {
            if (agent.equals(session.path("userAgent").asText())) {
                return session.path("current").asBoolean();
            }
        }
        throw new AssertionError("no session for " + agent + " in " + sessions);
    }

    private static java.util.List<String> agentsIn(JsonNode sessions) {
        java.util.List<String> agents = new java.util.ArrayList<>();
        sessions.forEach(session -> agents.add(session.path("userAgent").asText()));
        return agents;
    }
}
