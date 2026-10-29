package com.careeros.auth.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import com.careeros.auth.dto.LoginRequest;
import com.careeros.auth.entity.User;
import com.careeros.auth.repository.PasswordResetTokenRepository;
import com.careeros.auth.repository.UserProfileRepository;
import com.careeros.auth.repository.UserRepository;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;

/**
 * The sign-in's second step (roadmap 36.2). The password is checked first and answers exactly
 * what it always answered, so a stranger cannot learn from a login whether an account carries a
 * second factor. Only a matching password lets the factor speak: its {@code MFA_REQUIRED} and
 * {@code MFA_INVALID} reach the caller unchanged, which is the browser's cue to show a code
 * field. A successful sign-in hands the raw code to the factor with the principal's id -- the
 * service, not the browser, decides what the code stands for.
 */
class AuthServiceLoginTest {

    private static final UUID ALICE = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final String PASSWORD = "correct-horse-1";

    private final PasswordEncoder encoder = new BCryptPasswordEncoder(4);
    private UserRepository users;
    private MfaService mfa;
    private AuthService service;
    private User alice;

    @BeforeEach
    void setUp() {
        users = mock(UserRepository.class);
        mfa = mock(MfaService.class);
        service = new AuthService(users, mock(UserProfileRepository.class),
                mock(PasswordResetTokenRepository.class), mock(TokenService.class),
                encoder, mock(EmailSender.class), mfa, "https://careeros.example");

        alice = new User();
        alice.setId(ALICE);
        alice.setEmail("ada@example.invalid");
        alice.setPasswordHash(encoder.encode(PASSWORD));
        when(users.findByEmail("ada@example.invalid")).thenReturn(Optional.of(alice));
    }

    @Test
    void aWrongPasswordIsRefusedBeforeTheFactorIsEverConsulted() {
        assertThatThrownBy(() -> service.login(new LoginRequest("ada@example.invalid", "not-it-99", "123456")))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.code()).isEqualTo(ApiErrorCode.INVALID_CREDENTIALS));

        // The answer must not depend on the factor: a code guessed alongside a wrong password
        // learns nothing about this account, not even whether one is enrolled.
        verifyNoInteractions(mfa);
    }

    @Test
    void aDisabledAccountIsRefusedBeforeTheFactorIsEverConsulted() {
        alice.setStatus("disabled");

        assertThatThrownBy(() -> service.login(new LoginRequest("ada@example.invalid", PASSWORD, "123456")))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.code()).isEqualTo(ApiErrorCode.USER_DISABLED));

        verifyNoInteractions(mfa);
    }

    @Test
    void aMatchingPasswordOnAnEnrolledAccountSurfacesTheRequestForACode() {
        doThrow(new ApiException(ApiErrorCode.MFA_REQUIRED, "A code is needed"))
                .when(mfa).proveLogin(ALICE, null);

        assertThatThrownBy(() -> service.login(new LoginRequest("ada@example.invalid", PASSWORD, null)))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.code()).isEqualTo(ApiErrorCode.MFA_REQUIRED));
        verify(mfa).proveLogin(ALICE, null);
    }

    @Test
    void aWrongCodeReachesTheCallerAsTheFactorsOwnAnswer() {
        org.mockito.Mockito.doThrow(new ApiException(ApiErrorCode.MFA_INVALID, "Not right"))
                .when(mfa).proveLogin(ALICE, "000000");

        assertThatThrownBy(() -> service.login(new LoginRequest("ada@example.invalid", PASSWORD, "000000")))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.code()).isEqualTo(ApiErrorCode.MFA_INVALID));
    }

    @Test
    void aSuccessfulSignInHandsTheRawCodeToTheFactorUnderThePrincipalId() {
        User signedIn = service.login(new LoginRequest("ada@example.invalid", PASSWORD, " 424242 "));

        assertThat(signedIn).isSameAs(alice);
        // The code travels raw: normalizing it is the factor's job, done next to the seed and
        // the hashes, so a future login screen cannot invent a third spelling.
        verify(mfa).proveLogin(ALICE, " 424242 ");
    }

    @Test
    void anAccountWithoutAFactorSignsInWithNoCodeAtAll() {
        User signedIn = service.login(new LoginRequest("ada@example.invalid", PASSWORD, null));

        assertThat(signedIn).isSameAs(alice);
        // Whether a factor is on is the factor's question; the sign-in asks it with a null code
        // and lets it pass. The account row itself is not rewritten by a sign-in.
        verify(mfa).proveLogin(ALICE, null);
        verify(users, never()).save(any());
    }
}
