package com.careeros.auth.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.careeros.auth.dto.RegisterRequest;
import com.careeros.auth.entity.User;
import com.careeros.auth.repository.PasswordResetTokenRepository;
import com.careeros.auth.repository.UserProfileRepository;
import com.careeros.auth.repository.UserRepository;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;

/**
 * The register race, found by load-driving the endpoint: the pre-check and the INSERT are
 * two statements, so two concurrent registrations with the same address both pass
 * existsByEmail and both reach the write; the one that loses hits {@code users_email_key}
 * and surfaced as an unhandled 500. The reader deserves the same 409 the pre-check gives.
 */
class AuthServiceRegisterTest {

    private static final String PASSWORD = "correct-horse-1";

    private final PasswordEncoder encoder = new BCryptPasswordEncoder(4);
    private UserRepository users;
    private AuthService service;

    @BeforeEach
    void setUp() {
        users = mock(UserRepository.class);
        service = new AuthService(users, mock(UserProfileRepository.class),
                mock(PasswordResetTokenRepository.class), mock(TokenService.class),
                encoder, mock(EmailSender.class), mock(MfaService.class), "https://careeros.example");
    }

    @Test
    void anAddressThatLostTheInsertRaceAnswersWithTheSameConflictAsThePreCheck() {
        when(users.existsByEmail(any())).thenReturn(false);
        when(users.saveAndFlush(any(User.class))).thenThrow(new DataIntegrityViolationException(
                "could not execute statement [ERROR: duplicate key value violates unique constraint \"users_email_key\"]"));

        assertThatThrownBy(() -> service.register(new RegisterRequest("ada@example.invalid", PASSWORD, "Ada")))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.code()).isEqualTo(ApiErrorCode.EMAIL_ALREADY_REGISTERED));
    }

    @Test
    void anAddressThatPassedThePreCheckIsRegisteredAndStoredTrimmed() {
        User persisted = new User();
        when(users.existsByEmail(any())).thenReturn(false);
        when(users.saveAndFlush(any(User.class))).thenAnswer(invocation -> {
            User arg = invocation.getArgument(0);
            arg.setId(persisted.getId());
            persisted.setEmail(arg.getEmail());
            return arg;
        });

        User created = service.register(new RegisterRequest("  ada@example.invalid  ", PASSWORD, "  Ada  "));

        assertThat(created.getEmail()).isEqualTo("ada@example.invalid");
        assertThat(created.getDisplayName()).isEqualTo("Ada");
    }

    @Test
    void aDuplicatePreCheckAnswersWithTheConflictAndNeverReachesTheInsert() {
        when(users.existsByEmail("taken@example.invalid")).thenReturn(true);

        assertThatThrownBy(() -> service.register(new RegisterRequest("taken@example.invalid", PASSWORD, "Ada")))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.code()).isEqualTo(ApiErrorCode.EMAIL_ALREADY_REGISTERED));
    }
}
