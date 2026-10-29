package com.careeros.auth.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.auth.entity.User;
import com.careeros.auth.entity.UserMfa;
import com.careeros.auth.entity.UserMfaRecoveryCode;
import com.careeros.auth.mfa.MfaSecretCipher;
import com.careeros.auth.mfa.Totp;
import com.careeros.auth.repository.UserMfaRecoveryCodeRepository;
import com.careeros.auth.repository.UserMfaRepository;
import com.careeros.auth.repository.UserRepository;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;

/**
 * The rules behind enrollment: a pending seed is replaceable, an enabled one is not; activation
 * is the only way `active` turns true; the ten recovery codes exist in clear once and as hashes
 * afterwards. The repositories are mocks, so this is about what the service asks them to keep.
 */
class MfaServiceTest {

    private static final UUID ALICE = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final Instant NOW = Instant.parse("2026-10-30T09:00:00Z");
    private static final String PASSWORD = "correct-horse-battery-staple";

    private UserRepository users;
    private UserMfaRepository mfa;
    private UserMfaRecoveryCodeRepository recoveryCodes;
    private MfaSecretCipher cipher;
    private PasswordEncoder encoder;
    private MfaService service;

    @BeforeEach
    void setUp() {
        users = mock(UserRepository.class);
        mfa = mock(UserMfaRepository.class);
        recoveryCodes = mock(UserMfaRecoveryCodeRepository.class);
        cipher = new MfaSecretCipher("test-only-mfa-secret-0123456789abcdef");
        encoder = new BCryptPasswordEncoder(4);
        service = new MfaService(users, mfa, recoveryCodes, cipher, encoder);

        User alice = new User();
        alice.setId(ALICE);
        alice.setEmail("ada@example.invalid");
        alice.setPasswordHash(encoder.encode(PASSWORD));
        when(users.findById(ALICE)).thenReturn(Optional.of(alice));
    }

    @Test
    void enrollMintsASeedAndTheUriThatCarriesIt() {
        when(mfa.findByUserId(ALICE)).thenReturn(Optional.empty());

        MfaService.Enrollment enrollment = service.enroll(ALICE);

        assertThat(enrollment.secret()).hasSize(32).matches("[A-Z2-7]{32}");
        assertThat(enrollment.otpauthUri())
                .startsWith("otpauth://totp/AI%20Career%20OS:ada%40example.invalid?secret="
                        + enrollment.secret())
                .contains("&issuer=AI%20Career%20OS&algorithm=SHA1&digits=6&period=30");

        ArgumentCaptor<UserMfa> saved = ArgumentCaptor.forClass(UserMfa.class);
        verify(mfa).save(saved.capture());
        assertThat(saved.getValue().getUserId()).isEqualTo(ALICE);
        assertThat(saved.getValue().isActive()).as("unproven until a code answers").isFalse();
        assertThat(saved.getValue().getSecretCiphertext()).doesNotContain(enrollment.secret());
        assertThat(cipher.open(saved.getValue().getSecretCiphertext())).isEqualTo(enrollment.secret());
    }

    @Test
    void aSecondEnrollmentReplacesASeedThatWasNeverProven() {
        UserMfa pending = pending(Totp.newSecret());
        when(mfa.findByUserId(ALICE)).thenReturn(Optional.of(pending));

        MfaService.Enrollment enrollment = service.enroll(ALICE);

        assertThat(cipher.open(pending.getSecretCiphertext())).isEqualTo(enrollment.secret());
        assertThat(pending.isActive()).isFalse();
        verify(mfa).save(pending);
    }

    @Test
    void anEnabledSecondFactorRefusesANewSeed() {
        UserMfa active = pending(Totp.newSecret());
        active.setActive(true);
        when(mfa.findByUserId(ALICE)).thenReturn(Optional.of(active));

        assertThatThrownBy(() -> service.enroll(ALICE))
                .isInstanceOfSatisfying(ApiException.class, e ->
                        assertThat(e.code()).isEqualTo(ApiErrorCode.MFA_ALREADY_ACTIVE));
        verify(mfa, never()).save(any());
    }

    @Test
    void activationProvesTheCodeAndHandsOutTenPrintedSingleUseCodes() {
        String secret = Totp.newSecret();
        UserMfa pending = pending(secret);
        when(mfa.findByUserId(ALICE)).thenReturn(Optional.of(pending));

        String code = Totp.code(secret, Totp.stepAt(NOW));
        MfaService.Activation activation = service.activate(ALICE, PASSWORD, code, NOW);

        assertThat(activation.recoveryCodes()).hasSize(10).doesNotHaveDuplicates()
                .allMatch(printed -> printed.matches("[a-z2-7]{4}-[a-z2-7]{4}-[a-z2-7]{4}-[a-z2-7]{4}"));
        assertThat(pending.isActive()).isTrue();
        assertThat(pending.getActivatedAt().toInstant()).isEqualTo(NOW);
        assertThat(pending.getLastUsedStep()).isEqualTo(Totp.stepAt(NOW));

        ArgumentCaptor<UserMfaRecoveryCode> saved = ArgumentCaptor.forClass(UserMfaRecoveryCode.class);
        verify(recoveryCodes, times(10)).save(saved.capture());
        List<UserMfaRecoveryCode> rows = saved.getAllValues();
        assertThat(rows).allMatch(row -> ALICE.equals(row.getUserId()));
        for (int index = 0; index < rows.size(); index++) {
            String printed = activation.recoveryCodes().get(index);
            assertThat(rows.get(index).getCodeHash()).isNotEqualTo(printed);
            assertThat(encoder.matches(MfaService.normalizeRecoveryCode(printed),
                    rows.get(index).getCodeHash())).as("code %s is the stored hash", printed).isTrue();
        }
    }

    @Test
    void aWrongCodeLeavesTheEnrollmentPending() {
        String secret = Totp.newSecret();
        UserMfa pending = pending(secret);
        when(mfa.findByUserId(ALICE)).thenReturn(Optional.of(pending));

        String right = Totp.code(secret, Totp.stepAt(NOW));
        String wrong = right.equals("000000") ? "000001" : "000000";

        assertThatThrownBy(() -> service.activate(ALICE, PASSWORD, wrong, NOW))
                .isInstanceOfSatisfying(ApiException.class, e ->
                        assertThat(e.code()).isEqualTo(ApiErrorCode.MFA_CODE_INVALID));
        assertThat(pending.isActive()).isFalse();
        verify(mfa, never()).save(any());
        verify(recoveryCodes, never()).save(any());
    }

    @Test
    void aWrongPasswordCannotTurnTheFactorOn() {
        String secret = Totp.newSecret();
        UserMfa pending = pending(secret);
        when(mfa.findByUserId(ALICE)).thenReturn(Optional.of(pending));

        String rightCode = Totp.code(secret, Totp.stepAt(NOW));

        assertThatThrownBy(() -> service.activate(ALICE, "not-the-password", rightCode, NOW))
                .isInstanceOfSatisfying(ApiException.class, e ->
                        assertThat(e.code()).isEqualTo(ApiErrorCode.INVALID_CREDENTIALS));
        assertThat(pending.isActive()).as("the right code and the wrong password is not the owner").isFalse();
        verify(mfa, never()).save(any());
        verify(recoveryCodes, never()).save(any());
    }

    @Test
    void activationWithoutAStartedEnrollmentIsRefused() {
        when(mfa.findByUserId(ALICE)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.activate(ALICE, PASSWORD, "123456", NOW))
                .isInstanceOfSatisfying(ApiException.class, e ->
                        assertThat(e.code()).isEqualTo(ApiErrorCode.MFA_NOT_ENROLLED));
    }

    @Test
    void anEnabledSecondFactorCannotBeActivatedTwice() {
        UserMfa active = pending(Totp.newSecret());
        active.setActive(true);
        when(mfa.findByUserId(ALICE)).thenReturn(Optional.of(active));

        assertThatThrownBy(() -> service.activate(ALICE, PASSWORD, "123456", NOW))
                .isInstanceOfSatisfying(ApiException.class, e ->
                        assertThat(e.code()).isEqualTo(ApiErrorCode.MFA_ALREADY_ACTIVE));
    }

    @Test
    void statusNamesEnabledPendingAndNeither() {
        when(mfa.findByUserId(ALICE)).thenReturn(Optional.empty());
        assertThat(service.status(ALICE)).isEqualTo(new MfaService.Status(false, false));

        UserMfa pending = pending(Totp.newSecret());
        when(mfa.findByUserId(ALICE)).thenReturn(Optional.of(pending));
        assertThat(service.status(ALICE)).isEqualTo(new MfaService.Status(false, true));

        pending.setActive(true);
        assertThat(service.status(ALICE)).isEqualTo(new MfaService.Status(true, false));
    }

    @Test
    void aPrintedCodeAndATypedCodeAreTheSameString() {
        assertThat(MfaService.normalizeRecoveryCode(" ABcd-ef12 3456 ")).isEqualTo("abcdef123456");
        assertThat(MfaService.normalizeRecoveryCode(null)).isEmpty();
    }

    @Test
    void anAccountWithNoActiveFactorSignsInUnasked() {
        when(mfa.findByUserId(ALICE)).thenReturn(Optional.empty());
        service.proveLogin(ALICE, null, NOW);

        UserMfa pending = pending(Totp.newSecret());
        when(mfa.findByUserId(ALICE)).thenReturn(Optional.of(pending));
        service.proveLogin(ALICE, null, NOW);

        // A seed nobody proved cannot demand a code, and a login writes nothing of its own.
        verify(mfa, never()).save(any());
        verify(recoveryCodes, never()).findByUserId(any());
    }

    @Test
    void anActiveFactorDemandsACodeWhenTheLoginSendsNone() {
        UserMfa active = active(Totp.newSecret());
        when(mfa.findByUserId(ALICE)).thenReturn(Optional.of(active));

        for (String missing : new String[] {null, "", "   "}) {
            assertThatThrownBy(() -> service.proveLogin(ALICE, missing, NOW))
                    .isInstanceOfSatisfying(ApiException.class, e ->
                            assertThat(e.code()).isEqualTo(ApiErrorCode.MFA_REQUIRED));
        }
        verify(mfa, never()).save(any());
    }

    @Test
    void aRightCodeMovesTheSpentStepForward() {
        String secret = Totp.newSecret();
        UserMfa active = active(secret);
        active.setLastUsedStep(Totp.stepAt(NOW) - 3);
        when(mfa.findByUserId(ALICE)).thenReturn(Optional.of(active));

        service.proveLogin(ALICE, Totp.code(secret, Totp.stepAt(NOW)), NOW);

        assertThat(active.getLastUsedStep()).isEqualTo(Totp.stepAt(NOW));
        verify(mfa).save(active);
        verify(recoveryCodes, never()).save(any());
    }

    @Test
    void aCodeFromAStepTheAccountAlreadySpentIsRefused() {
        String secret = Totp.newSecret();
        UserMfa active = active(secret);
        active.setLastUsedStep(Totp.stepAt(NOW));
        when(mfa.findByUserId(ALICE)).thenReturn(Optional.of(active));

        assertThatThrownBy(() -> service.proveLogin(ALICE, Totp.code(secret, Totp.stepAt(NOW)), NOW))
                .isInstanceOfSatisfying(ApiException.class, e ->
                        assertThat(e.code()).isEqualTo(ApiErrorCode.MFA_INVALID));

        // The mark only moves forward; a replayed code changes nothing.
        assertThat(active.getLastUsedStep()).isEqualTo(Totp.stepAt(NOW));
        verify(mfa, never()).save(any());
    }

    @Test
    void aRecoveryCodeAnswersOnceAndThenIsSpent() {
        String secret = Totp.newSecret();
        UserMfa active = active(secret);
        when(mfa.findByUserId(ALICE)).thenReturn(Optional.of(active));

        UserMfaRecoveryCode printed = new UserMfaRecoveryCode();
        printed.setUserId(ALICE);
        printed.setCodeHash(encoder.encode(MfaService.normalizeRecoveryCode("abcd-ef23-4567-ghij")));
        when(recoveryCodes.findByUserId(ALICE)).thenReturn(List.of(printed));

        service.proveLogin(ALICE, "ABCD-EF23-4567-GHIJ", NOW);
        assertThat(printed.getUsedAt().toInstant()).isEqualTo(NOW);
        verify(recoveryCodes).save(printed);

        assertThatThrownBy(() -> service.proveLogin(ALICE, "abcd ef23 4567 ghij", NOW))
                .isInstanceOfSatisfying(ApiException.class, e ->
                        assertThat(e.code()).isEqualTo(ApiErrorCode.MFA_INVALID));
    }

    @Test
    void aWrongCodeTouchesNothing() {
        String secret = Totp.newSecret();
        UserMfa active = active(secret);
        active.setLastUsedStep(Totp.stepAt(NOW) - 1);
        when(mfa.findByUserId(ALICE)).thenReturn(Optional.of(active));

        String right = Totp.code(secret, Totp.stepAt(NOW));
        String wrong = right.equals("000000") ? "000001" : "000000";

        assertThatThrownBy(() -> service.proveLogin(ALICE, wrong, NOW))
                .isInstanceOfSatisfying(ApiException.class, e ->
                        assertThat(e.code()).isEqualTo(ApiErrorCode.MFA_INVALID));

        assertThat(active.getLastUsedStep()).isEqualTo(Totp.stepAt(NOW) - 1);
        verify(mfa, never()).save(any());
        verify(recoveryCodes, never()).save(any());
    }

    private UserMfa pending(String secret) {
        UserMfa row = new UserMfa();
        row.setUserId(ALICE);
        row.setSecretCiphertext(cipher.seal(secret));
        row.setActive(false);
        return row;
    }

    private UserMfa active(String secret) {
        UserMfa row = pending(secret);
        row.setActive(true);
        return row;
    }
}
