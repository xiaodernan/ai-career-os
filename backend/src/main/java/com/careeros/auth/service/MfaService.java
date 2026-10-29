package com.careeros.auth.service;

import com.careeros.auth.entity.User;
import com.careeros.auth.entity.UserMfa;
import com.careeros.auth.entity.UserMfaRecoveryCode;
import com.careeros.auth.mfa.Base32;
import com.careeros.auth.mfa.MfaSecretCipher;
import com.careeros.auth.mfa.Totp;
import com.careeros.auth.repository.UserMfaRecoveryCodeRepository;
import com.careeros.auth.repository.UserMfaRepository;
import com.careeros.auth.repository.UserRepository;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import java.security.SecureRandom;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.OptionalLong;
import java.util.UUID;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Enrolling the account's second factor (roadmap 36.1): show a seed, prove the reader's phone
 * holds it, and hand over the printed codes that stand in for the phone when it is lost.
 *
 * <p>Activation is the proof, so nothing about the account changes until a code from the
 * reader's own authenticator verifies against the seed. It asks for the account's current
 * password as well: a session alone could otherwise bolt a phone onto the account and outlive a
 * password change, locking the owner out of a factor they never set up. A pending enrollment can
 * be replaced (a reader who mistyped the seed into the phone, or abandoned the screen); an active
 * one cannot, because a stolen session could otherwise mint itself a fresh seed and quietly retire
 * the phone the real owner is holding. Turning two-factor off is its own operation (roadmap
 * 36.3), and it takes the password too.
 *
 * <p>Recovery codes are ordinary single-use passwords: hashed with the same encoder as the
 * account's password, normalized (lowercase, no spaces or hyphens) before hashing so the
 * printed spelling and the typed spelling are the same string, and replaced wholesale on every
 * activation. Their plaintext leaves the service exactly once, in this answer.
 */
@Service
public class MfaService {

    /** Ten is what a reader can print once and still find a spare in a year. */
    static final int RECOVERY_CODE_COUNT = 10;

    /** The name the authenticator's list shows; the label carries the account's address. */
    static final String ISSUER = "AI Career OS";

    /** 80 random bits per code, spelled as sixteen base32 characters in four groups. */
    private static final int RECOVERY_CODE_BYTES = 10;

    private static final SecureRandom RANDOM = new SecureRandom();

    private final UserRepository users;
    private final UserMfaRepository mfa;
    private final UserMfaRecoveryCodeRepository recoveryCodes;
    private final MfaSecretCipher cipher;
    private final PasswordEncoder passwordEncoder;

    public MfaService(UserRepository users, UserMfaRepository mfa,
                      UserMfaRecoveryCodeRepository recoveryCodes, MfaSecretCipher cipher,
                      PasswordEncoder passwordEncoder) {
        this.users = users;
        this.mfa = mfa;
        this.recoveryCodes = recoveryCodes;
        this.cipher = cipher;
        this.passwordEncoder = passwordEncoder;
    }

    /** The seed to show and the URI the authenticator scans; neither is on the account yet. */
    public record Enrollment(String secret, String otpauthUri) {
    }

    /** The one time the printed codes exist in clear, in the order the reader should file them. */
    public record Activation(List<String> recoveryCodes) {
    }

    /** Whether the second factor is in force, and whether a started enrollment is still waiting. */
    public record Status(boolean enabled, boolean pending) {
    }

    @Transactional
    public Enrollment enroll(UUID userId) {
        User user = users.findById(userId)
                .orElseThrow(() -> new ApiException(ApiErrorCode.USER_NOT_FOUND, "User not found"));
        UserMfa row = mfa.findByUserId(userId).orElse(null);
        if (row != null && row.isActive()) {
            throw new ApiException(ApiErrorCode.MFA_ALREADY_ACTIVE,
                    "Two-factor authentication is already on");
        }
        String secret = Totp.newSecret();
        if (row == null) {
            row = new UserMfa();
            row.setUserId(userId);
        }
        row.setSecretCiphertext(cipher.seal(secret));
        row.setActive(false);
        row.setActivatedAt(null);
        row.setLastUsedStep(null);
        mfa.save(row);
        // A pending row cannot own codes today; the delete is what keeps that true if a later
        // enrollment path ever writes them before activation.
        recoveryCodes.deleteByUserId(userId);
        return new Enrollment(secret, Totp.otpauthUri(ISSUER, user.getEmail(), secret));
    }

    @Transactional
    public Activation activate(UUID userId, String password, String code) {
        return activate(userId, password, code, Instant.now());
    }

    Activation activate(UUID userId, String password, String code, Instant now) {
        User user = users.findById(userId)
                .orElseThrow(() -> new ApiException(ApiErrorCode.USER_NOT_FOUND, "User not found"));
        if (!passwordEncoder.matches(password, user.getPasswordHash())) {
            throw new ApiException(ApiErrorCode.INVALID_CREDENTIALS, "Invalid credentials");
        }
        UserMfa row = mfa.findByUserId(userId)
                .orElseThrow(() -> new ApiException(ApiErrorCode.MFA_NOT_ENROLLED,
                        "Two-factor authentication has not been started for this account"));
        if (row.isActive()) {
            throw new ApiException(ApiErrorCode.MFA_ALREADY_ACTIVE,
                    "Two-factor authentication is already on");
        }
        String secret = cipher.open(row.getSecretCiphertext());
        OptionalLong matched = Totp.match(secret, code, now, Totp.DEFAULT_SKEW_STEPS);
        if (matched.isEmpty()) {
            throw new ApiException(ApiErrorCode.MFA_CODE_INVALID, "That six-digit code is not right");
        }
        row.setActive(true);
        row.setActivatedAt(OffsetDateTime.ofInstant(now, ZoneOffset.UTC));
        row.setLastUsedStep(matched.getAsLong());
        mfa.save(row);

        recoveryCodes.deleteByUserId(userId);
        List<String> printed = new ArrayList<>(RECOVERY_CODE_COUNT);
        for (int index = 0; index < RECOVERY_CODE_COUNT; index++) {
            String code4 = groupedRecoveryCode();
            UserMfaRecoveryCode entity = new UserMfaRecoveryCode();
            entity.setUserId(userId);
            entity.setCodeHash(passwordEncoder.encode(normalizeRecoveryCode(code4)));
            recoveryCodes.save(entity);
            printed.add(code4);
        }
        return new Activation(List.copyOf(printed));
    }

    @Transactional(readOnly = true)
    public Status status(UUID userId) {
        return mfa.findByUserId(userId)
                .map(row -> new Status(row.isActive(), !row.isActive()))
                .orElse(new Status(false, false));
    }

    /** Roadmap 36.2: the second factor as a login reads it, after the password has matched. */
    @Transactional
    public void proveLogin(UUID userId, String code) {
        proveLogin(userId, code, Instant.now());
    }

    /**
     * The login's half of the door. An account with no enabled factor passes unasked; an enabled
     * one demands a code ({@code MFA_REQUIRED}) and refuses a wrong one ({@code MFA_INVALID}).
     * A TOTP code that verifies moves the account's spent-step mark forward, and a recovery code
     * that answers is burned -- both writes ride the login's own transaction, so a login that
     * fails later does not spend a code the reader never got the benefit of.
     *
     * <p>The step mark is what makes a watched code useless: RFC 6238 repeats one number for a
     * whole 30-second window, so a shoulder-surfed code would otherwise open a second session.
     * A code from a step at or below the mark is refused even though its digits are right --
     * and it is refused as {@code MFA_INVALID} rather than as a replay-specific answer, because
     * "read the phone again" is the reader's whole next move either way.
     */
    void proveLogin(UUID userId, String code, Instant now) {
        UserMfa row = mfa.findByUserId(userId).filter(UserMfa::isActive).orElse(null);
        if (row == null) {
            return;
        }
        if (code == null || code.isBlank()) {
            throw new ApiException(ApiErrorCode.MFA_REQUIRED,
                    "This account asks for a six-digit code as a second step");
        }
        OptionalLong matched = Totp.match(cipher.open(row.getSecretCiphertext()), code, now,
                Totp.DEFAULT_SKEW_STEPS);
        if (matched.isPresent()) {
            if (row.getLastUsedStep() != null && matched.getAsLong() <= row.getLastUsedStep()) {
                throw new ApiException(ApiErrorCode.MFA_INVALID,
                        "That code is not right or was already used");
            }
            row.setLastUsedStep(matched.getAsLong());
            mfa.save(row);
            return;
        }
        String normalized = normalizeRecoveryCode(code);
        if (!normalized.isEmpty()) {
            for (UserMfaRecoveryCode candidate : recoveryCodes.findByUserId(userId)) {
                if (candidate.getUsedAt() != null) {
                    continue;
                }
                if (passwordEncoder.matches(normalized, candidate.getCodeHash())) {
                    candidate.setUsedAt(OffsetDateTime.ofInstant(now, ZoneOffset.UTC));
                    recoveryCodes.save(candidate);
                    return;
                }
            }
        }
        throw new ApiException(ApiErrorCode.MFA_INVALID, "That code is not right or was already used");
    }

    /**
     * The one spelling a recovery code is hashed and verified under: lowercase, no spaces or
     * hyphens. Printing adds the hyphens and verification strips them, so the reader's keyboard
     * cannot fail a code that is right.
     */
    public static String normalizeRecoveryCode(String raw) {
        return raw == null ? "" : raw.replace(" ", "").replace("-", "").trim().toLowerCase(Locale.ROOT);
    }

    private static String groupedRecoveryCode() {
        byte[] seed = new byte[RECOVERY_CODE_BYTES];
        RANDOM.nextBytes(seed);
        String plain = Base32.encode(seed).toLowerCase(Locale.ROOT);
        StringBuilder grouped = new StringBuilder(plain.length() + plain.length() / 4);
        for (int index = 0; index < plain.length(); index++) {
            if (index > 0 && index % 4 == 0) {
                grouped.append('-');
            }
            grouped.append(plain.charAt(index));
        }
        return grouped.toString();
    }
}
