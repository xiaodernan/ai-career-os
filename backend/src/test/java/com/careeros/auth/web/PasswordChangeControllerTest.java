package com.careeros.auth.web;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.careeros.auth.dto.PasswordChangeRequest;
import com.careeros.auth.service.AccountErasureService;
import com.careeros.auth.service.AuthService;
import com.careeros.auth.service.UserService;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUserArgumentResolver;
import com.careeros.common.EnvelopeAdvice;
import com.careeros.common.GlobalExceptionHandler;
import com.careeros.user.service.UserProfileService;
import com.careeros.user.web.UserController;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

/**
 * The two spellings of the password change (roadmap 24.1): the canonical `/me` surface and the
 * `/users/me` alias the browser calls. The service is mocked, so what is pinned here is the
 * route contract -- the envelope, the validation, the unauthenticated answer, and the fact
 * that both spellings reach one method with the principal's id.
 *
 * <p>The rules behind the method (re-authentication, same-password refusal, revocation) are
 * {@link com.careeros.auth.service.AuthServicePasswordChangeTest}'s. The one claim this class
 * adds is that the answer carries no trace of either password: a response body that echoed
 * the new value would leak it into browser history, logs and screenshots.
 */
class PasswordChangeControllerTest {

    private static final UUID ALICE = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final String BODY = "{\"currentPassword\":\"old-password-1\",\"newPassword\":\"new-password-2\"}";

    private AuthService authService;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        authService = mock(AuthService.class);
        AccountErasureService erasure = mock(AccountErasureService.class);
        mvc = MockMvcBuilders.standaloneSetup(
                        new MeController(mock(UserService.class), authService, erasure),
                        new UserController(mock(UserService.class), mock(UserProfileService.class),
                                authService, erasure))
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
    void bothSpellingsAnswerChangedTrueAndHandTheServiceThePrincipalAndTheParsedBody() throws Exception {
        PasswordChangeRequest expected = new PasswordChangeRequest("old-password-1", "new-password-2");

        for (String path : List.of("/api/v1/me/password", "/api/v1/users/me/password")) {
            mvc.perform(patch(path).contentType(MediaType.APPLICATION_JSON).content(BODY))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.success").value(true))
                    .andExpect(jsonPath("$.data.changed").value(true));
        }

        verify(authService, times(2)).changePassword(ALICE, expected);
    }

    @Test
    void theAnswerCarriesTheFlagAndNotEitherPassword() throws Exception {
        MvcResult result = mvc.perform(patch("/api/v1/me/password")
                        .contentType(MediaType.APPLICATION_JSON).content(BODY))
                .andExpect(status().isOk())
                .andReturn();

        assertThat(result.getResponse().getContentAsString())
                .doesNotContain("old-password-1")
                .doesNotContain("new-password-2");
    }

    @Test
    void aRefusedCurrentPasswordTravelsAsThe401Envelope() throws Exception {
        doThrow(new ApiException(ApiErrorCode.INVALID_CREDENTIALS, "Current password is incorrect"))
                .when(authService).changePassword(any(), any());

        mvc.perform(patch("/api/v1/me/password")
                        .contentType(MediaType.APPLICATION_JSON).content(BODY))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.error.code").value("INVALID_CREDENTIALS"))
                .andExpect(jsonPath("$.error.message").value("Current password is incorrect"));
    }

    @Test
    void aSamePasswordRefusalKeepsItsOwnCodeSoTheScreenCanSaySomethingPrecise() throws Exception {
        doThrow(new ApiException(ApiErrorCode.PASSWORD_UNCHANGED,
                "New password must differ from the current one"))
                .when(authService).changePassword(any(), any());

        mvc.perform(patch("/api/v1/users/me/password")
                        .contentType(MediaType.APPLICATION_JSON).content(BODY))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("PASSWORD_UNCHANGED"));
    }

    @Test
    void aShortNewPasswordIsRefusedBeforeTheServiceRuns() throws Exception {
        mvc.perform(patch("/api/v1/me/password")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"currentPassword\":\"old-password-1\",\"newPassword\":\"short\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("VALIDATION_FAILED"))
                .andExpect(jsonPath("$.error.details[0].field").value("newPassword"));

        verifyNoInteractions(authService);
    }

    @Test
    void anEmptyCurrentPasswordIsARefusalNotAReAuthentication() throws Exception {
        mvc.perform(patch("/api/v1/me/password")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"currentPassword\":\"\",\"newPassword\":\"new-password-2\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.details[0].field").value("currentPassword"));

        verifyNoInteractions(authService);
    }

    @Test
    void anUnauthenticatedCallerIsRefusedOnBothSpellings() throws Exception {
        SecurityContextHolder.clearContext();

        for (String path : List.of("/api/v1/me/password", "/api/v1/users/me/password")) {
            mvc.perform(patch(path).contentType(MediaType.APPLICATION_JSON).content(BODY))
                    .andExpect(status().isUnauthorized())
                    .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_JSON))
                    .andExpect(jsonPath("$.error.code").value("UNAUTHORIZED"));
        }

        verifyNoInteractions(authService);
    }
}
