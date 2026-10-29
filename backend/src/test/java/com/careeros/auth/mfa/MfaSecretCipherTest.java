package com.careeros.auth.mfa;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

/** Sealed at rest, unreadable without the key, and every seal a different string. */
class MfaSecretCipherTest {

    private static final String KEY = "test-only-mfa-secret-0123456789abcdef";

    private final MfaSecretCipher cipher = new MfaSecretCipher(KEY);

    @Test
    void aSealedSeedOpensToItselfAndNotToThePlaintext() {
        String seed = Totp.newSecret();
        String sealed = cipher.seal(seed);

        assertThat(sealed).doesNotContain(seed);
        assertThat(cipher.open(sealed)).isEqualTo(seed);
    }

    @Test
    void theSameSeedSealsToADifferentStringEveryTime() {
        String seed = Totp.newSecret();
        assertThat(cipher.seal(seed)).isNotEqualTo(cipher.seal(seed));
    }

    @Test
    void aFlippedCharacterIsARefusedOpen() {
        String sealed = cipher.seal(Totp.newSecret());
        char last = sealed.charAt(sealed.length() - 1);
        String tampered = sealed.substring(0, sealed.length() - 1) + (last == 'A' ? 'B' : 'A');

        assertThatThrownBy(() -> cipher.open(tampered)).isInstanceOf(IllegalStateException.class);
    }

    @Test
    void anotherKeyCannotOpenIt() {
        String sealed = cipher.seal(Totp.newSecret());
        MfaSecretCipher rotated = new MfaSecretCipher("a-different-mfa-secret-0123456789abcdef");

        assertThatThrownBy(() -> rotated.open(sealed)).isInstanceOf(IllegalStateException.class);
    }

    @Test
    void anEmptyKeyIsRefusedWhenTheBeanIsBuilt() {
        assertThatThrownBy(() -> new MfaSecretCipher(" ")).isInstanceOf(IllegalStateException.class);
    }
}
