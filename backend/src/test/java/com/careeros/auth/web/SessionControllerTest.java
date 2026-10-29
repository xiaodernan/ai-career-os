package com.careeros.auth.web;

import static org.hamcrest.Matchers.hasSize;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.careeros.auth.dto.SessionResponse;
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
import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

/**
 * The two spellings of the session surface (roadmap 25): list the account's open doors,
 * close one by family id, close all. The service is mocked — the folding and refusal rules
 * live in {@link com.careeros.auth.service.TokenServiceSessionsTest}; what is pinned here
 * is the route contract, the envelope, and that the principal's id is the only account
 * either verb can reach.
 */
class SessionControllerTest {

    private static final UUID ALICE = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final UUID FAMILY = UUID.fromString("22222222-2222-4222-8222-222222222222");

    private TokenService tokenService;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        tokenService = mock(TokenService.class);
        mvc = MockMvcBuilders.standaloneSetup(
                        new MeController(mock(UserService.class), mock(AuthService.class),
                                mock(AccountErasureService.class), tokenService,
                                mock(EmailChangeService.class)),
                        new UserController(mock(UserService.class), mock(UserProfileService.class),
                                mock(AuthService.class), mock(AccountErasureService.class), tokenService,
                                mock(EmailChangeService.class)))
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
    void bothSpellingsListTheCallersSessionsInTheEnvelope() throws Exception {
        when(tokenService.listSessions(ALICE)).thenReturn(List.of(
                new SessionResponse(FAMILY, "Laptop/1.0", "203.0.113.1",
                        OffsetDateTime.parse("2026-10-01T09:00:00Z"),
                        OffsetDateTime.parse("2026-10-02T10:00:00Z"),
                        OffsetDateTime.parse("2026-11-01T09:00:00Z"))));

        for (String path : List.of("/api/v1/me/sessions", "/api/v1/users/me/sessions")) {
            mvc.perform(get(path))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.success").value(true))
                    .andExpect(jsonPath("$.data", hasSize(1)))
                    .andExpect(jsonPath("$.data[0].id").value(FAMILY.toString()))
                    .andExpect(jsonPath("$.data[0].userAgent").value("Laptop/1.0"))
                    .andExpect(jsonPath("$.data[0].clientIp").value("203.0.113.1"));
        }

        verify(tokenService, times(2)).listSessions(ALICE);
    }

    @Test
    void bothSpellingsCloseOneFamilyAndHandTheServiceThePrincipal() throws Exception {
        for (String path : List.of("/api/v1/me/sessions/" + FAMILY,
                "/api/v1/users/me/sessions/" + FAMILY)) {
            mvc.perform(delete(path))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.data.revoked").value(true));
        }

        verify(tokenService, times(2)).revokeSession(ALICE, FAMILY);
    }

    @Test
    void bothSpellingsCloseEveryFamily() throws Exception {
        for (String path : List.of("/api/v1/me/sessions", "/api/v1/users/me/sessions")) {
            mvc.perform(delete(path))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.data.revoked").value(true));
        }

        verify(tokenService, times(2)).revokeAllForUser(ALICE);
    }

    @Test
    void aFamilyThatIsNotTheCallersTravelsAsOne404() throws Exception {
        doThrow(new ApiException(ApiErrorCode.LOGIN_SESSION_NOT_FOUND, "Session not found"))
                .when(tokenService).revokeSession(any(), any());

        mvc.perform(delete("/api/v1/me/sessions/" + FAMILY))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error.code").value("LOGIN_SESSION_NOT_FOUND"))
                .andExpect(jsonPath("$.error.message").value("Session not found"));
    }

    @Test
    void anUnauthenticatedCallerIsRefusedOnEveryVerb() throws Exception {
        SecurityContextHolder.clearContext();

        for (String path : List.of("/api/v1/me/sessions", "/api/v1/users/me/sessions")) {
            mvc.perform(get(path))
                    .andExpect(status().isUnauthorized())
                    .andExpect(jsonPath("$.error.code").value("UNAUTHORIZED"));
            mvc.perform(delete(path))
                    .andExpect(status().isUnauthorized())
                    .andExpect(jsonPath("$.error.code").value("UNAUTHORIZED"));
        }
        mvc.perform(delete("/api/v1/me/sessions/" + FAMILY))
                .andExpect(status().isUnauthorized());

        verifyNoInteractions(tokenService);
    }
}
