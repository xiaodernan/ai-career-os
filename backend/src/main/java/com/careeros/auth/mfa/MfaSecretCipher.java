package com.careeros.auth.mfa;

import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.Base64;
import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/**
 * Seals the TOTP seed a reader's authenticator carries, so a database dump is not a list of
 * every account's future second factor.
 *
 * <p>AES-256-GCM under a key derived from {@code app.security.mfa-secret}: the configured value
 * is a passphrase of whatever length the operator chose, so the key is its SHA-256 digest rather
 * than the bytes themselves -- AES wants exactly 256 bits and a short env value would otherwise
 * fail to key the cipher. The nonce is a fresh 12 random bytes per seal, prepended to the
 * ciphertext; the tag is GCM's default 128 bits. Each sealed value is therefore different even
 * for the same seed, and a flipped bit anywhere is a failed open rather than a different seed.
 *
 * <p>Failure is {@link IllegalStateException}, not a checked exception: there is no request a
 * caller can make to fix it. The two causes are a rotated {@code app.security.mfa-secret} and a
 * damaged row, and both mean the same thing to the account -- this seed cannot be read. A printed
 * recovery code does not help either: the proof opens the seed before it tries the printed set, so
 * the login and every proof route refuse. The operator path is the runbook's lockout section --
 * restore the old secret, or delete the account's {@code user_mfa} and
 * {@code user_mfa_recovery_codes} rows so it returns to password-only sign-in.
 */
@Component
public class MfaSecretCipher {

    private static final int IV_BYTES = 12;
    private static final int TAG_BITS = 128;

    private static final SecureRandom RANDOM = new SecureRandom();

    private final SecretKeySpec key;

    public MfaSecretCipher(@Value("${app.security.mfa-secret}") String secret) {
        if (secret == null || secret.isBlank()) {
            throw new IllegalStateException("app.security.mfa-secret is empty: no TOTP seed can be sealed");
        }
        this.key = new SecretKeySpec(sha256(secret), "AES");
    }

    public String seal(String plaintext) {
        try {
            byte[] iv = new byte[IV_BYTES];
            RANDOM.nextBytes(iv);
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.ENCRYPT_MODE, key, new GCMParameterSpec(TAG_BITS, iv));
            byte[] sealed = cipher.doFinal(plaintext.getBytes(StandardCharsets.UTF_8));
            byte[] out = new byte[iv.length + sealed.length];
            System.arraycopy(iv, 0, out, 0, iv.length);
            System.arraycopy(sealed, 0, out, iv.length, sealed.length);
            return Base64.getUrlEncoder().withoutPadding().encodeToString(out);
        } catch (GeneralSecurityException e) {
            throw new IllegalStateException("the TOTP seed could not be sealed", e);
        }
    }

    public String open(String sealed) {
        try {
            byte[] raw = Base64.getUrlDecoder().decode(sealed);
            if (raw.length <= IV_BYTES) {
                throw new IllegalStateException("the sealed TOTP seed is too short to carry an IV and a tag");
            }
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.DECRYPT_MODE, key,
                    new GCMParameterSpec(TAG_BITS, raw, 0, IV_BYTES));
            byte[] plain = cipher.doFinal(raw, IV_BYTES, raw.length - IV_BYTES);
            return new String(plain, StandardCharsets.UTF_8);
        } catch (GeneralSecurityException | IllegalArgumentException e) {
            throw new IllegalStateException(
                    "the sealed TOTP seed cannot be opened with this app.security.mfa-secret", e);
        }
    }

    private static byte[] sha256(String value) {
        try {
            return MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8));
        } catch (GeneralSecurityException e) {
            throw new IllegalStateException("SHA-256 is required and missing here", e);
        }
    }
}
