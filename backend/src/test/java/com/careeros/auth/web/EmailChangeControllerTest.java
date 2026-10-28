package com.careeros.auth.web;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.careeros.auth.dto.EmailChangeRequest;
import com.careeros.auth.service.AccountErasureService;
import com.careeros.auth.service.AuthService;
import com.careeros.auth.service.EmailChangeService;
import com.careeros.auth.service.TokenService;
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
 * The route contract of the address move (roadmap 26): the two signed-in spellings
 * (`/me/email-change`, `/users/me/email-change`) that ask, and the public
 * `/auth/email-change/confirm` the new mailbox calls. The service's rules live in
 * {@link com.careeros.auth.service.EmailChangeServiceTest}; what is pinned here is the
 * `{sent:true}` / `{changed:true}` envelopes, the refusal codes on the wire, the validation
 * that runs before the service, the unauthenticated answer, that the password is not echoed,
 * and that confirmation needs no session at all.
 */
class EmailChangeControllerTest {

    private static final UUID ALICE = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final String PASSWORD = "Str0ngPassphrase!23";
    private static final String NEW_EMAIL = "ada.new@example.invalid";
    private static final String BODY =
            "{\"password\":\"" + PASSWORD + "\",\"newEmail\":\"" + NEW_EMAIL + "\"}";
    private static final String TOKEN = "Zm9vYmFyYmF6cXV4enl4enl4enl4enl4enl4enl4enl4";

    private EmailChangeService emailChange;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        emailChange = mock(EmailChangeService.class);
        mvc = MockMvcBuilders.standaloneSetup(
                        new MeController(mock(UserService.class), mock(AuthService.class),
                                mock(AccountErasureService.class), mock(TokenService.class), emailChange),
                        new UserController(mock(UserService.class), mock(UserProfileService.class),
                                mock(AuthService.class), mock(AccountErasureService.class),
                                mock(TokenService.class), emailChange),
                        new AuthController(mock(AuthService.class), mock(TokenService.class), emailChange))
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
    void bothSpellingsAnswerSentTrueAndHandTheServiceThePrincipalAndTheParsedBody() throws Exception {
        EmailChangeRequest expected = new EmailChangeRequest(PASSWORD, NEW_EMAIL);

        for (String path : List.of("/api/v1/me/email-change", "/api/v1/users/me/email-change")) {
            mvc.perform(post(path).contentType(MediaType.APPLICATION_JSON).content(BODY))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.success").value(true))
                    .andExpect(jsonPath("$.data.sent").value(true));
        }

        verify(emailChange, times(2)).request(ALICE, expected);
    }

    @Test
    void theAnswerCarriesTheFlagAndNotThePassword() throws Exception {
        MvcResult result = mvc.perform(post("/api/v1/me/email-change")
                        .contentType(MediaType.APPLICATION_JSON).content(BODY))
                .andExpect(status().isOk())
                .andReturn();

        assertThat(result.getResponse().getContentAsString()).doesNotContain(PASSWORD);
    }

    @Test
    void aWrongPasswordTravelsAsThe401Envelope() throws Exception {
        doThrow(new ApiException(ApiErrorCode.INVALID_CREDENTIALS, "Password is incorrect"))
                .when(emailChange).request(any(), any());

        mvc.perform(post("/api/v1/me/email-change").contentType(MediaType.APPLICATION_JSON).content(BODY))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.error.code").value("INVALID_CREDENTIALS"));
    }

    @Test
    void theTwoAddressRefusalsKeepTheirOwnCodesSoTheScreenCanSayWhatIsWrong() throws Exception {
        doThrow(new ApiException(ApiErrorCode.EMAIL_UNCHANGED, "That is already the account's address"))
                .when(emailChange).request(any(), any());
        mvc.perform(post("/api/v1/me/email-change").contentType(MediaType.APPLICATION_JSON).content(BODY))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("EMAIL_UNCHANGED"));

        doThrow(new ApiException(ApiErrorCode.EMAIL_ALREADY_REGISTERED, "Email is already registered"))
                .when(emailChange).request(any(), any());
        mvc.perform(post("/api/v1/users/me/email-change").contentType(MediaType.APPLICATION_JSON).content(BODY))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.error.code").value("EMAIL_ALREADY_REGISTERED"));
    }

    @Test
    void anInvalidAddressOrAnEmptyPasswordIsRefusedBeforeTheServiceRuns() throws Exception {
        mvc.perform(post("/api/v1/me/email-change").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"password\":\"" + PASSWORD + "\",\"newEmail\":\"not-an-address\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("VALIDATION_FAILED"))
                .andExpect(jsonPath("$.error.details[0].field").value("newEmail"));

        mvc.perform(post("/api/v1/users/me/email-change").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"password\":\"\",\"newEmail\":\"" + NEW_EMAIL + "\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.details[0].field").value("password"));

        verifyNoInteractions(emailChange);
    }

    @Test
    void theNewMailboxConfirmsWithoutASessionAndTheAnswerCarriesOnlyTheFlag() throws Exception {
        SecurityContextHolder.clearContext();

        MvcResult result = mvc.perform(post("/api/v1/auth/email-change/confirm")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"token\":\"" + TOKEN + "\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.changed").value(true))
                .andReturn();

        String body = result.getResponse().getContentAsString();
        assertThat(body).doesNotContain(TOKEN);
        verify(emailChange).confirm(TOKEN);
    }

    @Test
    void aRefusedLinkTravelsAsThe400Envelope() throws Exception {
        doThrow(new ApiException(ApiErrorCode.EMAIL_CHANGE_INVALID, "Invalid email change token"))
                .when(emailChange).confirm(any());

        mvc.perform(post("/api/v1/auth/email-change/confirm")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"token\":\"" + TOKEN + "\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("EMAIL_CHANGE_INVALID"));
    }

    @Test
    void anEmptyConfirmationTokenIsARefusalBeforeTheServiceRuns() throws Exception {
        mvc.perform(post("/api/v1/auth/email-change/confirm").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"token\":\"\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("VALIDATION_FAILED"))
                .andExpect(jsonPath("$.error.details[0].field").value("token"));

        verifyNoInteractions(emailChange);
    }

    @Test
    void anUnauthenticatedCallerIsRefusedOnBothSignedInSpellings() throws Exception {
        SecurityContextHolder.clearContext();

        for (String path : List.of("/api/v1/me/email-change", "/api/v1/users/me/email-change")) {
            mvc.perform(post(path).contentType(MediaType.APPLICATION_JSON).content(BODY))
                    .andExpect(status().isUnauthorized())
                    .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_JSON))
                    .andExpect(jsonPath("$.error.code").value("UNAUTHORIZED"));
        }

        verifyNoInteractions(emailChange);
    }
}
