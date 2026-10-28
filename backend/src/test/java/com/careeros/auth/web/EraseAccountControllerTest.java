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

import com.careeros.auth.dto.EraseAccountRequest;
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
 * The erasure's two spellings (roadmap 24.2): the canonical `/me/erase` and the `/users/me`
 * alias the browser calls. The service is mocked and its rules are
 * {@link com.careeros.auth.service.AccountErasureServiceTest}'s; what is pinned here is the
 * route contract -- the `{erased: true}` envelope, the two refusal codes, the validation
 * failure, the unauthenticated answer, and that neither spelling echoes the password.
 *
 * <p>The route answers 200 rather than 204 on purpose: the screen needs a body to know the
 * account is gone before it clears its own state, and every other mutation in this API answers
 * with a small object.
 */
class EraseAccountControllerTest {

    private static final UUID ALICE = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final String PASSWORD = "Str0ngPassphrase!23";
    private static final String BODY =
            "{\"password\":\"" + PASSWORD + "\",\"confirmEmail\":\"ada@example.invalid\"}";

    private AccountErasureService erasure;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        erasure = mock(AccountErasureService.class);
        AuthService authService = mock(AuthService.class);
        com.careeros.auth.service.TokenService tokenService = mock(com.careeros.auth.service.TokenService.class);
        mvc = MockMvcBuilders.standaloneSetup(
                        new MeController(mock(UserService.class), authService, erasure, tokenService),
                        new UserController(mock(UserService.class), mock(UserProfileService.class),
                                authService, erasure, tokenService))
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
    void bothSpellingsAnswerErasedTrueAndHandTheServiceThePrincipalAndTheParsedBody() throws Exception {
        EraseAccountRequest expected = new EraseAccountRequest(PASSWORD, "ada@example.invalid");

        for (String path : List.of("/api/v1/me/erase", "/api/v1/users/me/erase")) {
            mvc.perform(post(path).contentType(MediaType.APPLICATION_JSON).content(BODY))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.success").value(true))
                    .andExpect(jsonPath("$.data.erased").value(true));
        }

        verify(erasure, times(2)).erase(ALICE, expected);
    }

    @Test
    void theAnswerCarriesTheFlagAndNotThePassword() throws Exception {
        MvcResult result = mvc.perform(post("/api/v1/me/erase")
                        .contentType(MediaType.APPLICATION_JSON).content(BODY))
                .andExpect(status().isOk())
                .andReturn();

        assertThat(result.getResponse().getContentAsString()).doesNotContain(PASSWORD);
    }

    @Test
    void aWrongPasswordTravelsAsThe401Envelope() throws Exception {
        doThrow(new ApiException(ApiErrorCode.INVALID_CREDENTIALS, "Password is incorrect"))
                .when(erasure).erase(any(), any());

        mvc.perform(post("/api/v1/me/erase").contentType(MediaType.APPLICATION_JSON).content(BODY))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.error.code").value("INVALID_CREDENTIALS"));
    }

    @Test
    void aTypedAddressForAnotherAccountKeepsItsOwnCodeSoTheScreenCanSayWhatIsWrong() throws Exception {
        doThrow(new ApiException(ApiErrorCode.CONFIRMATION_MISMATCH,
                "The typed email does not match this account"))
                .when(erasure).erase(any(), any());

        mvc.perform(post("/api/v1/users/me/erase").contentType(MediaType.APPLICATION_JSON).content(BODY))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("CONFIRMATION_MISMATCH"));
    }

    @Test
    void anEmptyConfirmationIsARefusalBeforeTheServiceRuns() throws Exception {
        mvc.perform(post("/api/v1/me/erase")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"password\":\"" + PASSWORD + "\",\"confirmEmail\":\"\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("VALIDATION_FAILED"))
                .andExpect(jsonPath("$.error.details[0].field").value("confirmEmail"));

        verifyNoInteractions(erasure);
    }

    @Test
    void anUnauthenticatedCallerIsRefusedOnBothSpellings() throws Exception {
        SecurityContextHolder.clearContext();

        for (String path : List.of("/api/v1/me/erase", "/api/v1/users/me/erase")) {
            mvc.perform(post(path).contentType(MediaType.APPLICATION_JSON).content(BODY))
                    .andExpect(status().isUnauthorized())
                    .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_JSON))
                    .andExpect(jsonPath("$.error.code").value("UNAUTHORIZED"));
        }

        verifyNoInteractions(erasure);
    }
}
