package com.careeros;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.careeros.auth.service.EmailSender;
import com.fasterxml.jackson.databind.JsonNode;
import java.util.Map;
import java.util.UUID;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MvcResult;

/**
 * The address move against the real schema (roadmap 26).
 *
 * <p>The raw confirmation token exists only in the outbound letter -- the row keeps its
 * SHA-256 hash -- so the transport is captured and read the way the new mailbox would. The
 * test walks the whole promise: refusal before a letter, the letter to the new address and
 * the warning to the old one, a bogus link refused, the real link moving `users.email`,
 * signing every refresh token out, letting the old address fail and the new one sign in with
 * the unchanged password, the link refusing a second answer, and a neighbour account whose
 * address and sessions are untouched.
 */
class EmailChangeIT extends ApiIntegrationTest {

    private static final String PASSWORD = "Str0ngPassphrase!23";

    @MockitoBean
    private EmailSender emailSender;

    @Test
    void theMoveWaitsForTheNewMailboxAndTouchesNobodyElse() throws Exception {
        String aliceEmail = "move-alice-" + UUID.randomUUID() + "@example.com";
        String newEmail = "move-alice-new-" + UUID.randomUUID() + "@example.com";
        String bobEmail = "move-bob-" + UUID.randomUUID() + "@example.com";

        JsonNode alice = registerAccount(aliceEmail);
        String aliceAccess = alice.path("tokens").path("accessToken").asText();
        String aliceRefresh = alice.path("tokens").path("refreshToken").asText();
        JsonNode bob = registerAccount(bobEmail);
        String bobAccess = bob.path("tokens").path("accessToken").asText();
        String bobRefresh = bob.path("tokens").path("refreshToken").asText();

        // Asking costs the password; the wrong one mails nothing.
        mvc.perform(post("/api/v1/me/email-change")
                        .header("Authorization", "Bearer " + aliceAccess)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(Map.of("password", "NotThePassword!1", "newEmail", newEmail))))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.error.code").value("CURRENT_PASSWORD_INCORRECT"));
        // The address the account already has is a refusal, not a letter to itself.
        mvc.perform(post("/api/v1/users/me/email-change")
                        .header("Authorization", "Bearer " + aliceAccess)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(Map.of("password", PASSWORD, "newEmail", aliceEmail.toUpperCase()))))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("EMAIL_UNCHANGED"));
        // A neighbour's address is taken.
        mvc.perform(post("/api/v1/me/email-change")
                        .header("Authorization", "Bearer " + aliceAccess)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(Map.of("password", PASSWORD, "newEmail", bobEmail))))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.error.code").value("EMAIL_ALREADY_REGISTERED"));
        verifyNoInteractions(emailSender);

        // The real ask: a link for the claimed mailbox, a warning for the one on the account.
        mvc.perform(post("/api/v1/me/email-change")
                        .header("Authorization", "Bearer " + aliceAccess)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(Map.of("password", PASSWORD, "newEmail", newEmail))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.sent").value(true));

        ArgumentCaptor<String> letter = ArgumentCaptor.forClass(String.class);
        verify(emailSender).send(eq(newEmail), anyString(), letter.capture());
        Matcher linked = Pattern.compile("/confirm-email\\?token=([A-Za-z0-9_-]{43})")
                .matcher(letter.getValue());
        assertThat(linked.find()).as("the confirmation mail must carry an openable link").isTrue();
        String rawToken = linked.group(1);
        ArgumentCaptor<String> warning = ArgumentCaptor.forClass(String.class);
        verify(emailSender).send(eq(aliceEmail), anyString(), warning.capture());
        assertThat(warning.getValue()).contains(newEmail);

        // Nothing has moved yet.
        mvc.perform(get("/api/v1/me").header("Authorization", "Bearer " + aliceAccess))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.email").value(aliceEmail));

        // A link nobody issued is refused.
        mvc.perform(post("/api/v1/auth/email-change/confirm")
                        .header("X-Forwarded-For", freshIp())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"token\":\"bogus-email-change-token\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("EMAIL_CHANGE_INVALID"));

        // The new mailbox answers; the address moves and every session signs out.
        mvc.perform(post("/api/v1/auth/email-change/confirm")
                        .header("X-Forwarded-For", freshIp())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(Map.of("token", rawToken))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.changed").value(true));

        verify(emailSender, times(2)).send(eq(newEmail), anyString(), anyString());
        verify(emailSender, times(2)).send(eq(aliceEmail), anyString(), anyString());

        mvc.perform(post("/api/v1/auth/refresh")
                        .header("X-Forwarded-For", freshIp())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(Map.of("refreshToken", aliceRefresh))))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.error.code").value("TOKEN_REUSED"));

        // The old address no longer signs in; the new one does, with the same password.
        mvc.perform(post("/api/v1/auth/login")
                        .header("X-Forwarded-For", freshIp())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(Map.of("email", aliceEmail, "password", PASSWORD))))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.error.code").value("INVALID_CREDENTIALS"));
        MvcResult signedIn = mvc.perform(post("/api/v1/auth/login")
                        .header("X-Forwarded-For", freshIp())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(Map.of("email", newEmail, "password", PASSWORD))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.user.email").value(newEmail))
                .andReturn();
        String newAccess = data(signedIn).path("tokens").path("accessToken").asText();
        mvc.perform(get("/api/v1/me").header("Authorization", "Bearer " + newAccess))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.email").value(newEmail));

        // The link answered once and cannot answer again.
        mvc.perform(post("/api/v1/auth/email-change/confirm")
                        .header("X-Forwarded-For", freshIp())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(Map.of("token", rawToken))))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("EMAIL_CHANGE_INVALID"));

        // The neighbour's address and sessions never moved.
        mvc.perform(get("/api/v1/me").header("Authorization", "Bearer " + bobAccess))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.email").value(bobEmail));
        mvc.perform(post("/api/v1/auth/refresh")
                        .header("X-Forwarded-For", freshIp())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(Map.of("refreshToken", bobRefresh))))
                .andExpect(status().isOk());
    }

    private JsonNode registerAccount(String email) throws Exception {
        MvcResult result = mvc.perform(post("/api/v1/auth/register")
                        .header("X-Forwarded-For", freshIp())
                        .header("User-Agent", "JUnit/email-change")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"email\":\"" + email + "\",\"password\":\"" + PASSWORD + "\","
                                + "\"displayName\":\"Move Tester\"}"))
                .andExpect(status().isCreated())
                .andReturn();
        return data(result);
    }

    private static JsonNode data(MvcResult result) throws Exception {
        return MAPPER.readTree(result.getResponse().getContentAsString()).path("data");
    }
}
