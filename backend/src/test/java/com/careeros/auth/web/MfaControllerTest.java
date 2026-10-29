package com.careeros.auth.web;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.careeros.auth.service.MfaService;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUserArgumentResolver;
import com.careeros.common.EnvelopeAdvice;
import com.careeros.common.GlobalExceptionHandler;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

/**
 * The five routes of the second door, pinned to their contract: the signed-in caller's id
 * reaches the service, the body is validated before it does, and the refusals travel as
 * their own codes so the browser's table can say something precise.
 */
class MfaControllerTest {

    private static final UUID ALICE = UUID.fromString("11111111-1111-4111-8111-111111111111");

    private MfaService mfa;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        mfa = mock(MfaService.class);
        mvc = MockMvcBuilders.standaloneSetup(new MfaController(mfa))
                .setControllerAdvice(new EnvelopeAdvice(), new GlobalExceptionHandler())
                .setCustomArgumentResolvers(new CurrentUserArgumentResolver())
                .build();
        SecurityContextHolder.getContext().setAuthentication(new UsernamePasswordAuthenticationToken(
                new AuthUser(ALICE, "ada@example.invalid", "user"), null, List.of()));
    }

    @AfterEach
    void clearPrincipal() {
        SecurityContextHolder.clearContext();
    }

    @Test
    void statusAnswersThePrincipalAndTheTwoFlags() throws Exception {
        when(mfa.status(ALICE)).thenReturn(new MfaService.Status(true, false, 6));

        mvc.perform(get("/api/v1/me/mfa"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.enabled").value(true))
                .andExpect(jsonPath("$.data.pending").value(false))
                .andExpect(jsonPath("$.data.recoveryCodesRemaining").value(6));
    }

    @Test
    void enrollAnswersTheSeedAndTheUri() throws Exception {
        when(mfa.enroll(ALICE)).thenReturn(new MfaService.Enrollment("JBSWY3DPEHPK3PXP",
                "otpauth://totp/AI%20Career%20OS:ada@example.invalid?secret=JBSWY3DPEHPK3PXP"));

        mvc.perform(post("/api/v1/me/mfa/enroll"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.secret").value("JBSWY3DPEHPK3PXP"))
                .andExpect(jsonPath("$.data.otpauthUri").value(
                        "otpauth://totp/AI%20Career%20OS:ada@example.invalid?secret=JBSWY3DPEHPK3PXP"));
    }

    @Test
    void activateHandsTheParsedPasswordAndCodeToTheServiceAndAnswersTheCodes() throws Exception {
        when(mfa.activate(ALICE, "correct-horse-battery-staple", "123456")).thenReturn(new MfaService.Activation(
                List.of("abcd-efgh-ijkl-mnop", "qrst-uvwx-yz23-4567")));

        mvc.perform(post("/api/v1/me/mfa/activate")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"password\":\"correct-horse-battery-staple\",\"code\":\"123456\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.recoveryCodes[0]").value("abcd-efgh-ijkl-mnop"))
                .andExpect(jsonPath("$.data.recoveryCodes[1]").value("qrst-uvwx-yz23-4567"));
    }

    @Test
    void aCodeThatIsNotSixDigitsIsRefusedBeforeTheServiceRuns() throws Exception {
        for (String body : List.of(
                "{\"password\":\"correct-horse-battery-staple\",\"code\":\"12ab56\"}",
                "{\"password\":\"correct-horse-battery-staple\",\"code\":\"12345\"}",
                "{\"password\":\"correct-horse-battery-staple\"}")) {
            mvc.perform(post("/api/v1/me/mfa/activate")
                            .contentType(MediaType.APPLICATION_JSON).content(body))
                    .andExpect(status().isBadRequest())
                    .andExpect(jsonPath("$.error.code").value("VALIDATION_FAILED"))
                    .andExpect(jsonPath("$.error.details[0].field").value("code"));
        }
        // The password is the other half of the proof: a code without it never reaches the service.
        mvc.perform(post("/api/v1/me/mfa/activate")
                        .contentType(MediaType.APPLICATION_JSON).content("{\"code\":\"123456\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("VALIDATION_FAILED"))
                .andExpect(jsonPath("$.error.details[0].field").value("password"));

        verifyNoInteractions(mfa);
    }

    @Test
    void anEnabledSecondFactorTravelsAsAConflict() throws Exception {
        doThrow(new ApiException(ApiErrorCode.MFA_ALREADY_ACTIVE, "Two-factor authentication is already on"))
                .when(mfa).enroll(any());

        mvc.perform(post("/api/v1/me/mfa/enroll"))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.error.code").value("MFA_ALREADY_ACTIVE"));
    }

    @Test
    void aWrongCodeTravelsAsItsOwnUnauthorized() throws Exception {
        doThrow(new ApiException(ApiErrorCode.MFA_CODE_INVALID, "That six-digit code is not right"))
                .when(mfa).activate(any(), any(), any());

        mvc.perform(post("/api/v1/me/mfa/activate")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"password\":\"correct-horse-battery-staple\",\"code\":\"123456\"}"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.error.code").value("MFA_CODE_INVALID"))
                .andExpect(jsonPath("$.error.message").value("That six-digit code is not right"));
    }

    @Test
    void aWrongPasswordTravelsAsAPlainUnauthorized() throws Exception {
        doThrow(new ApiException(ApiErrorCode.INVALID_CREDENTIALS, "Invalid credentials"))
                .when(mfa).activate(any(), any(), any());

        mvc.perform(post("/api/v1/me/mfa/activate")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"password\":\"not-the-password\",\"code\":\"123456\"}"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.error.code").value("INVALID_CREDENTIALS"));
    }

    @Test
    void aReprintHandsTheProofToTheServiceAndAnswersTheFreshSheet() throws Exception {
        when(mfa.reissueRecoveryCodes(ALICE, "correct-horse-battery-staple", "abcd-efgh-ijkl-mnop"))
                .thenReturn(new MfaService.Activation(List.of("wxyz-2345-6789-abcd")));

        mvc.perform(post("/api/v1/me/mfa/recovery-codes")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"password\":\"correct-horse-battery-staple\","
                                + "\"code\":\"abcd-efgh-ijkl-mnop\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.recoveryCodes[0]").value("wxyz-2345-6789-abcd"));
    }

    @Test
    void eitherFieldMissingIsRefusedBeforeTheServiceRuns() throws Exception {
        for (String path : List.of("/api/v1/me/mfa/recovery-codes", "/api/v1/me/mfa/disable")) {
            mvc.perform(post(path)
                            .contentType(MediaType.APPLICATION_JSON)
                            .content("{\"code\":\"123456\"}"))
                    .andExpect(status().isBadRequest())
                    .andExpect(jsonPath("$.error.code").value("VALIDATION_FAILED"))
                    .andExpect(jsonPath("$.error.details[0].field").value("password"));
            mvc.perform(post(path)
                            .contentType(MediaType.APPLICATION_JSON)
                            .content("{\"password\":\"correct-horse-battery-staple\"}"))
                    .andExpect(status().isBadRequest())
                    .andExpect(jsonPath("$.error.details[0].field").value("code"));
        }

        verifyNoInteractions(mfa);
    }

    @Test
    void disableAnswersTrueAfterTheServiceTurnsTheDoorOff() throws Exception {
        mvc.perform(post("/api/v1/me/mfa/disable")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"password\":\"correct-horse-battery-staple\",\"code\":\"123456\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.disabled").value(true));

        verify(mfa).disable(ALICE, "correct-horse-battery-staple", "123456");
    }

    @Test
    void anUnauthenticatedCallerIsRefusedOnEveryRoute() throws Exception {
        SecurityContextHolder.clearContext();

        mvc.perform(get("/api/v1/me/mfa"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.error.code").value("UNAUTHORIZED"));
        mvc.perform(post("/api/v1/me/mfa/enroll"))
                .andExpect(status().isUnauthorized());
        mvc.perform(post("/api/v1/me/mfa/activate")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"password\":\"correct-horse-battery-staple\",\"code\":\"123456\"}"))
                .andExpect(status().isUnauthorized());
        mvc.perform(post("/api/v1/me/mfa/recovery-codes")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"password\":\"correct-horse-battery-staple\",\"code\":\"123456\"}"))
                .andExpect(status().isUnauthorized());
        mvc.perform(post("/api/v1/me/mfa/disable")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"password\":\"correct-horse-battery-staple\",\"code\":\"123456\"}"))
                .andExpect(status().isUnauthorized());

        verifyNoInteractions(mfa);
        assertThat(ALICE).isNotNull();
    }
}
