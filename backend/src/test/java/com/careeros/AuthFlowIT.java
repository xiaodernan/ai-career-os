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

    /**
     * The second step, end to end (roadmap 36.2). The unit tests pin each branch against mocks;
     * this walks the real seed, cipher, repositories and login path: the password alone stops
     * with {@code MFA_REQUIRED}, a wrong code with {@code MFA_INVALID}, the phone's code opens
     * the door exactly once, and a printed recovery code opens it once and never again.
     *
     * <p>Activation spends the step its code answers for, so the login code is computed one step
     * ahead -- what the reader's phone shows after the setup screen closes. Everything on one IP
     * stays under the auth bucket: one registration and six sign-ins.
     */
    @Test
    void anEnrolledAccountCannotSignInWithThePasswordAlone() throws Exception {
        String ip = freshIp();
        String email = "mfa-login-it@example.com";
        String password = "Str0ngPassphrase!23";
        String accessToken = register(ip, email).path("tokens").path("accessToken").asText();

        String enrollment = mvc.perform(post("/api/v1/me/mfa/enroll")
                        .header("Authorization", "Bearer " + accessToken))
                .andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString();
        String secret = JSON.readTree(enrollment).path("data").path("secret").asText();

        long step = com.careeros.auth.mfa.Totp.stepAt(java.time.Instant.now());
        String activation = mvc.perform(post("/api/v1/me/mfa/activate")
                        .header("Authorization", "Bearer " + accessToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(JSON.writeValueAsString(java.util.Map.of(
                                "password", password,
                                "code", com.careeros.auth.mfa.Totp.code(secret, step)))))
                .andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString();
        String recoveryCode = JSON.readTree(activation).path("data").path("recoveryCodes").get(0).asText();

        String loginBody = "{\"email\":\"%s\",\"password\":\"%s\"%s}";
        // The password opens nothing by itself, and a wrong password is still the old answer --
        // the two are asked in that order, so the factor never tells a stranger anything.
        mvc.perform(auth(post("/api/v1/auth/login"), ip)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(loginBody.formatted(email, "NotThePassword!1", "")))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.error.code").value("INVALID_CREDENTIALS"));
        mvc.perform(auth(post("/api/v1/auth/login"), ip)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(loginBody.formatted(email, password, "")))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.error.code").value("MFA_REQUIRED"));

        String laterCode = com.careeros.auth.mfa.Totp.code(secret, step + 1);
        String wrongCode = laterCode.equals("000000") ? "000001" : "000000";
        mvc.perform(auth(post("/api/v1/auth/login"), ip)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(loginBody.formatted(email, password,
                                ",\"code\":\"" + wrongCode + "\"")))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.error.code").value("MFA_INVALID"));

        mvc.perform(auth(post("/api/v1/auth/login"), ip)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(loginBody.formatted(email, password,
                                ",\"code\":\"" + laterCode + "\"")))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.user.email").value(email));

        // RFC 6238 repeats one number for a whole window; a watched code must not open a second
        // session even though its digits are still right.
        mvc.perform(auth(post("/api/v1/auth/login"), ip)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(loginBody.formatted(email, password,
                                ",\"code\":\"" + laterCode + "\"")))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.error.code").value("MFA_INVALID"));

        // The printed fallback answers once, in the spelling it was printed in.
        mvc.perform(auth(post("/api/v1/auth/login"), ip)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(loginBody.formatted(email, password,
                                ",\"code\":\"" + recoveryCode + "\"")))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.user.email").value(email));
        mvc.perform(auth(post("/api/v1/auth/login"), ip)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(loginBody.formatted(email, password,
                                ",\"code\":\"" + recoveryCode + "\"")))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.error.code").value("MFA_INVALID"));
    }

    /**
     * Roadmap 36.3 end to end: the sheet can replace itself, the replaced sheet is dead, and the
     * door comes off with a printed code. The unit tests pin the order of the deletes against
     * mocks; this walks the real rows, BCrypt hashes and the login that follows.
     */
    @Test
    void anActivatedAccountCanReplaceItsSheetAndTakeTheDoorOff() throws Exception {
        String ip = freshIp();
        String email = "mfa-door-it@example.com";
        String password = "Str0ngPassphrase!23";
        String accessToken = register(ip, email).path("tokens").path("accessToken").asText();

        String enrollment = mvc.perform(post("/api/v1/me/mfa/enroll")
                        .header("Authorization", "Bearer " + accessToken))
                .andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString();
        String secret = JSON.readTree(enrollment).path("data").path("secret").asText();

        long step = com.careeros.auth.mfa.Totp.stepAt(java.time.Instant.now());
        String activation = mvc.perform(post("/api/v1/me/mfa/activate")
                        .header("Authorization", "Bearer " + accessToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(JSON.writeValueAsString(java.util.Map.of(
                                "password", password,
                                "code", com.careeros.auth.mfa.Totp.code(secret, step)))))
                .andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString();
        JsonNode oldSheet = JSON.readTree(activation).path("data").path("recoveryCodes");
        assertThat(oldSheet.size()).isEqualTo(10);

        // A printed code is proof enough to replace the sheet; the answer is a fresh ten.
        String reprintBody = mvc.perform(post("/api/v1/me/mfa/recovery-codes")
                        .header("Authorization", "Bearer " + accessToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(JSON.writeValueAsString(java.util.Map.of(
                                "password", password, "code", oldSheet.get(1).asText()))))
                .andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString();
        JsonNode freshSheet = JSON.readTree(reprintBody).path("data").path("recoveryCodes");
        assertThat(freshSheet.size()).isEqualTo(10);
        java.util.Set<String> previous = new java.util.HashSet<>();
        oldSheet.forEach(code -> previous.add(code.asText()));
        freshSheet.forEach(code -> assertThat(previous).doesNotContain(code.asText()));
        mvc.perform(get("/api/v1/me/mfa").header("Authorization", "Bearer " + accessToken))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.enabled").value(true))
                .andExpect(jsonPath("$.data.recoveryCodesRemaining").value(10));

        // The replaced sheet is dead in both directions: its rows were deleted, not just marked,
        // so one of its codes cannot even re-authenticate a reprint of its successor.
        mvc.perform(post("/api/v1/me/mfa/recovery-codes")
                        .header("Authorization", "Bearer " + accessToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(JSON.writeValueAsString(java.util.Map.of(
                                "password", password, "code", oldSheet.get(2).asText()))))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.error.code").value("MFA_INVALID"));

        // The door comes off with a printed code from the current sheet, and answers true.
        mvc.perform(post("/api/v1/me/mfa/disable")
                        .header("Authorization", "Bearer " + accessToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(JSON.writeValueAsString(java.util.Map.of(
                                "password", password, "code", freshSheet.get(0).asText()))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.disabled").value(true));

        // The next sign-in asks for the password alone, and the status says nothing is left.
        mvc.perform(auth(post("/api/v1/auth/login"), ip)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(JSON.writeValueAsString(java.util.Map.of(
                                "email", email, "password", password))))
                .andExpect(status().isOk());
        mvc.perform(get("/api/v1/me/mfa").header("Authorization", "Bearer " + accessToken))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.enabled").value(false))
                .andExpect(jsonPath("$.data.pending").value(false))
                .andExpect(jsonPath("$.data.recoveryCodesRemaining").value(0));
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
