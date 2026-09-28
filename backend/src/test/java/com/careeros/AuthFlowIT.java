package com.careeros;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.containsString;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.careeros.auth.service.EmailSender;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.concurrent.atomic.AtomicLong;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.request.MockHttpServletRequestBuilder;

class AuthFlowIT extends AbstractIntegrationTest {

    private static final ObjectMapper JSON = new ObjectMapper();
    private static final AtomicLong IP_SEQ = new AtomicLong(100);

    /** The dev transport is the only place a raw reset token is legible; capture what it sends. */
    @MockitoBean
    private EmailSender emailSender;

    /** One fresh client IP per logical session: the auth rate limit (10/min) is per IP. */
    private static String freshIp() {
        long n = IP_SEQ.incrementAndGet();
        return "10.77." + (n % 250) + "." + (n / 250 % 250);
    }

    private JsonNode register(String ip, String email) throws Exception {
        String body = mvc.perform(auth(post("/api/v1/auth/register"), ip)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"email":"%s","password":"Str0ngPassphrase!23","displayName":"Test User"}"""
                                .formatted(email)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.success").value(true))
                .andReturn().getResponse().getContentAsString();
        return JSON.readTree(body).path("data");
    }

    private MockHttpServletRequestBuilder auth(MockHttpServletRequestBuilder builder, String ip) {
        return builder.header("X-Forwarded-For", ip);
    }

    @Test
    void registerReturnsEnvelopeWithTokensAndMeIsAccessible() throws Exception {
        String ip = freshIp();
        JsonNode data = register(ip, "reg-it@example.com");
        String accessToken = data.path("tokens").path("accessToken").asText();
        JsonNode user = data.path("user");
        org.junit.jupiter.api.Assertions.assertEquals("reg-it@example.com", user.path("email").asText());
        org.junit.jupiter.api.Assertions.assertEquals("Bearer",
                data.path("tokens").path("tokenType").asText());

        mvc.perform(get("/api/v1/me").header("Authorization", "Bearer " + accessToken))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.email").value("reg-it@example.com"))
                .andExpect(jsonPath("$.data.displayName").value("Test User"));
    }

    @Test
    void loginWithWrongPasswordIsRejectedWithEnvelope() throws Exception {
        String ip = freshIp();
        register(ip, "wrongpw-it@example.com");
        mvc.perform(auth(post("/api/v1/auth/login"), ip)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"email":"wrongpw-it@example.com","password":"NotThePassword!1"}"""))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.success").value(false))
                .andExpect(jsonPath("$.error.code").value("INVALID_CREDENTIALS"));
    }

    @Test
    void refreshRotatesAndReuseRevokesWholeFamily() throws Exception {
        String ip = freshIp();
        String firstRefresh = register(ip, "rotation-it@example.com")
                .path("tokens").path("refreshToken").asText();

        String rotatedBody = mvc.perform(auth(post("/api/v1/auth/refresh"), ip)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(JSON.writeValueAsString(java.util.Map.of("refreshToken", firstRefresh))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.refreshToken").isString())
                .andReturn().getResponse().getContentAsString();
        String secondRefresh = JSON.readTree(rotatedBody).path("data").path("refreshToken").asText();

        mvc.perform(auth(post("/api/v1/auth/refresh"), ip)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(JSON.writeValueAsString(java.util.Map.of("refreshToken", firstRefresh))))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.error.code").value("TOKEN_REUSED"));

        mvc.perform(auth(post("/api/v1/auth/refresh"), ip)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(JSON.writeValueAsString(java.util.Map.of("refreshToken", secondRefresh))))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.error.code").value("TOKEN_REUSED"));
    }

    @Test
    void logoutInvalidatesRefreshToken() throws Exception {
        String ip = freshIp();
        String refreshToken = register(ip, "logout-it@example.com")
                .path("tokens").path("refreshToken").asText();

        mvc.perform(auth(post("/api/v1/auth/logout"), ip)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(JSON.writeValueAsString(java.util.Map.of("refreshToken", refreshToken))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.loggedOut").value(true));

        mvc.perform(auth(post("/api/v1/auth/refresh"), ip)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(JSON.writeValueAsString(java.util.Map.of("refreshToken", refreshToken))))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void forgotPasswordIsEnumeratingSafeAndResetRejectsBogusToken() throws Exception {
        String ip = freshIp();
        mvc.perform(auth(post("/api/v1/auth/password/forgot"), ip)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"email":"nobody-at-all@example.com"}"""))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.accepted").value(true));

        mvc.perform(auth(post("/api/v1/auth/password/reset"), ip)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"token":"bogus-reset-token","newPassword":"AnotherStr0ng!Pass"}"""))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("RESET_TOKEN_INVALID"));
    }

    /**
     * The half of the reset flow the test above cannot see: that a token issued by `forgot`
     * actually works. Rejection-only coverage would still pass if `forgot` wrote a token no
     * reset could ever spend.
     *
     * The raw token exists nowhere but the outbound mail — the row keeps only its SHA-256 hash —
     * so the dev transport is captured and read the way an inbox would be.
     */
    @Test
    void resetPasswordSpendsTheIssuedTokenAndEndsEverySession() throws Exception {
        String ip = freshIp();
        String email = "reset-happy-it@example.com";
        String refreshToken = register(ip, email).path("tokens").path("refreshToken").asText();

        mvc.perform(auth(post("/api/v1/auth/password/forgot"), ip)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(JSON.writeValueAsString(java.util.Map.of("email", email))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.accepted").value(true));

        ArgumentCaptor<String> body = ArgumentCaptor.forClass(String.class);
        verify(emailSender).send(eq(email), anyString(), body.capture());
        // `TokenHasher.generateOpaqueToken` is 32 random bytes as unpadded base64url: 43 chars.
        // The link is matched first: a token the mail prints but never links is a token the
        // reset screen's URL pass cannot see, which is exactly the dead end this asserts away.
        Matcher linked = Pattern.compile("/reset-password\\?token=([A-Za-z0-9_-]{43})")
                .matcher(body.getValue());
        assertThat(linked.find()).as("the reset mail must carry an openable link").isTrue();
        String rawToken = linked.group(1);
        // The token is on a line of its own as well, for a mail client that mangles the link
        // (and for whoever reads the dev transport's console output).
        assertThat(body.getValue()).contains("\n" + rawToken);

        mvc.perform(auth(post("/api/v1/auth/password/reset"), ip)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"token":"%s","newPassword":"Br4ndNewPassphrase"}"""
                                .formatted(rawToken)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.reset").value(true));

        mvc.perform(auth(post("/api/v1/auth/login"), ip)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(JSON.writeValueAsString(
                                java.util.Map.of("email", email, "password", "Br4ndNewPassphrase"))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.user.email").value(email));

        mvc.perform(auth(post("/api/v1/auth/login"), ip)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(JSON.writeValueAsString(
                                java.util.Map.of("email", email, "password", "Str0ngPassphrase!23"))))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.error.code").value("INVALID_CREDENTIALS"));

        // A password change is a logout everywhere: the refresh token from before must be dead.
        mvc.perform(auth(post("/api/v1/auth/refresh"), ip)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(JSON.writeValueAsString(
                                java.util.Map.of("refreshToken", refreshToken))))
                .andExpect(status().isUnauthorized());

        // And the token itself is single-use.
        mvc.perform(auth(post("/api/v1/auth/password/reset"), ip)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"token":"%s","newPassword":"YetAnotherPassphrase1"}"""
                                .formatted(rawToken)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("RESET_TOKEN_INVALID"));
    }

    @Test
    void validationFailureReturnsStructuredDetails() throws Exception {
        String ip = freshIp();
        mvc.perform(auth(post("/api/v1/auth/register"), ip)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"email":"not-an-email","password":"short","displayName":""}"""))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.success").value(false))
                .andExpect(jsonPath("$.error.code").value("VALIDATION_FAILED"))
                .andExpect(jsonPath("$.error.details[0].field").exists())
                .andExpect(jsonPath("$.error.details[0].message").exists());
    }

    @Test
    void meRequiresAuthenticationAndIdorSmokeKeepsOwnDataOnly() throws Exception {
        mvc.perform(get("/api/v1/me"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.error.code").value("UNAUTHORIZED"));

        String ipA = freshIp();
        String ipB = freshIp();
        String tokenA = register(ipA, "user-a-it@example.com").path("tokens").path("accessToken").asText();
        String tokenB = register(ipB, "user-b-it@example.com").path("tokens").path("accessToken").asText();

        // /api/v1/me derives the subject purely from the bearer token: B can never read A's profile.
        mvc.perform(get("/api/v1/me").header("Authorization", "Bearer " + tokenB))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.email").value("user-b-it@example.com"))
                .andExpect(jsonPath("$.data.email").value(
                        org.hamcrest.Matchers.not(containsString("user-a"))));

        mvc.perform(patch("/api/v1/me").header("Authorization", "Bearer " + tokenA)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"headline":"Backend engineer","preferences":{"theme":"dark"}}"""))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.headline").value("Backend engineer"))
                .andExpect(jsonPath("$.data.preferences.theme").value("dark"));

        mvc.perform(get("/api/v1/me").header("Authorization", "Bearer " + tokenA)
                        .header("X-Forwarded-For", ipA))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.email").value("user-a-it@example.com"));
    }
}
