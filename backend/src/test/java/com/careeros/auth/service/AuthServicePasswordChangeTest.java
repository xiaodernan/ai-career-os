package com.careeros.auth.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import com.careeros.auth.dto.PasswordChangeRequest;
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
import org.mockito.ArgumentCaptor;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;

/**
 * Changing the password from inside a signed-in session (roadmap 24.1).
 *
 * <p>Four claims. The current password is the re-authentication: a wrong one changes nothing
 * and leaves every session alive, so a borrowed laptop cannot lock the owner out. A new value
 * equal to the old one is refused rather than silently "changed", because the change would buy
 * nothing and would still sign every other device out. The new value is encoded, never stored
 * raw. And every refresh token is revoked on success -- the reset path's response to a change
 * -- so a reader who suspects a compromise keeps their open tab for its short access-token
 * life and nothing more. The account id is the principal's; the request has no field for it.
 */
class AuthServicePasswordChangeTest {

    private static final UUID ALICE = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final String CURRENT = "old-password-1";
    private static final String NEXT = "new-password-2";

    private final PasswordEncoder encoder = new BCryptPasswordEncoder(4);
    private UserRepository users;
    private PasswordResetTokenRepository resetTokens;
    private TokenService tokenService;
    private AuthService service;
    private User alice;

    @BeforeEach
    void setUp() {
        users = mock(UserRepository.class);
        resetTokens = mock(PasswordResetTokenRepository.class);
        tokenService = mock(TokenService.class);
        service = new AuthService(users, mock(UserProfileRepository.class), resetTokens, tokenService,
                encoder, mock(EmailSender.class), "https://careeros.example");

        alice = new User();
        alice.setId(ALICE);
        alice.setEmail("ada@example.invalid");
        alice.setPasswordHash(encoder.encode(CURRENT));
        when(users.findById(ALICE)).thenReturn(Optional.of(alice));
    }

    @Test
    void theRightCurrentPasswordIsReplacedAndEveryRefreshTokenIsRevoked() {
        service.changePassword(ALICE, new PasswordChangeRequest(CURRENT, NEXT));

        ArgumentCaptor<User> saved = ArgumentCaptor.forClass(User.class);
        verify(users).save(saved.capture());
        assertThat(encoder.matches(NEXT, saved.getValue().getPasswordHash())).isTrue();
        assertThat(encoder.matches(CURRENT, saved.getValue().getPasswordHash())).isFalse();
        assertThat(saved.getValue().getPasswordHash()).isNotEqualTo(NEXT);
        // The revocation takes the principal's id, which no field of the request can name.
        verify(tokenService).revokeAllForUser(ALICE);
        // A password change is not a reset link: the forgot-password rows are untouched.
        verifyNoInteractions(resetTokens);
    }

    @Test
    void aWrongCurrentPasswordChangesNothingAndKeepsEverySessionAlive() {
        assertThatThrownBy(() -> service.changePassword(ALICE, new PasswordChangeRequest("not-it-99", NEXT)))
                .isInstanceOfSatisfying(ApiException.class, e -> {
                    assertThat(e.code()).isEqualTo(ApiErrorCode.CURRENT_PASSWORD_INCORRECT);
                    assertThat(e.getMessage()).isEqualTo("Current password is incorrect");
                });

        verify(users, never()).save(any());
        verifyNoInteractions(tokenService);
    }

    @Test
    void aNewPasswordEqualToTheOldOneIsRefusedRatherThanReportedAsAChange() {
        assertThatThrownBy(() -> service.changePassword(ALICE, new PasswordChangeRequest(CURRENT, CURRENT)))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.code()).isEqualTo(ApiErrorCode.PASSWORD_UNCHANGED));

        verify(users, never()).save(any());
        verifyNoInteractions(tokenService);
    }

    @Test
    void anAccountThatVanishedBehindAValidTokenIsA404AndTouchesNoSession() {
        when(users.findById(ALICE)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.changePassword(ALICE, new PasswordChangeRequest(CURRENT, NEXT)))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.code()).isEqualTo(ApiErrorCode.USER_NOT_FOUND));

        verifyNoInteractions(tokenService);
    }
}
