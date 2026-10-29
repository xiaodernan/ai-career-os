package com.careeros.auth.mfa;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.List;
import org.junit.jupiter.api.Test;

/**
 * The RFC's own numbers (6238 Appendix B, reduced to the six digits every authenticator app
 * shows) plus the window and spelling rules the enrollment surface relies on. A TOTP
 * implementation that is only tested against itself agrees with its own bugs; the vectors are
 * the only thing here that an outside source authored.
 */
class TotpTest {

    /** RFC 4226's seed -- the ASCII digits 0..9 repeated -- spelled as base32. */
    private static final String RFC_SECRET = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ";

    @Test
    void theRfc6238VectorsAnswerTheirSixDigitSuffixes() {
        vector(59L, "287082");
        vector(1111111109L, "081804");
        vector(1111111111L, "050471");
        vector(1234567890L, "005924");
        vector(2000000000L, "279037");
        vector(20000000000L, "353130");
    }

    private static void vector(long epochSecond, String sixDigits) {
        long step = Totp.stepAt(Instant.ofEpochSecond(epochSecond));
        assertThat(Totp.code(RFC_SECRET, step)).as("T=%s", epochSecond).isEqualTo(sixDigits);
    }

    @Test
    void matchAcceptsExactlyOneStepEitherSideOfTheMoment() {
        Instant at = Instant.ofEpochSecond(1111111111L);
        long step = Totp.stepAt(at);

        assertThat(Totp.match(RFC_SECRET, Totp.code(RFC_SECRET, step), at, 1)).hasValue(step);
        assertThat(Totp.match(RFC_SECRET, Totp.code(RFC_SECRET, step - 1), at, 1)).hasValue(step - 1);
        assertThat(Totp.match(RFC_SECRET, Totp.code(RFC_SECRET, step + 1), at, 1)).hasValue(step + 1);
        assertThat(Totp.match(RFC_SECRET, Totp.code(RFC_SECRET, step - 2), at, 1)).isEmpty();
        assertThat(Totp.match(RFC_SECRET, Totp.code(RFC_SECRET, step + 2), at, 1)).isEmpty();
    }

    @Test
    void anythingThatIsNotSixDigitsIsNotACode() {
        Instant at = Instant.ofEpochSecond(1111111111L);
        for (String broken : List.of("", "12345", "1234567", "abcdef", "12-34-56", "   ")) {
            assertThat(Totp.match(RFC_SECRET, broken, at, 1)).as("%r", broken).isEmpty();
        }
        assertThat(Totp.match(RFC_SECRET, null, at, 1)).isEmpty();
    }

    @Test
    void aSpacedCodeIsTheSameCode() {
        Instant at = Instant.ofEpochSecond(59);
        assertThat(Totp.match(RFC_SECRET, "287 082", at, 1)).hasValue(1L);
    }

    @Test
    void aFreshSecretIsTwentyBytesOfBase32AndNeverRepeats() {
        String secret = Totp.newSecret();

        assertThat(secret).hasSize(32).matches("[A-Z2-7]{32}");
        assertThat(Base32.decode(secret)).hasSize(20);
        assertThat(Totp.newSecret()).isNotEqualTo(secret);
    }

    @Test
    void base32RoundTripsAndForgivesWhatAReaderTypes() {
        byte[] seed = Base32.decode(RFC_SECRET);

        assertThat(new String(seed, StandardCharsets.US_ASCII)).isEqualTo("12345678901234567890");
        assertThat(Base32.encode(seed)).isEqualTo(RFC_SECRET);
        assertThat(Base32.decode("gezd gnbv-gy3t-qojq gezd gnbv gy3t qojq===")).isEqualTo(seed);
        assertThatThrownBy(() -> Base32.decode("GEZD1")).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> Base32.decode("")).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void theUriCarriesTheParametersAnAuthenticatorExpects() {
        assertThat(Totp.otpauthUri("AI Career OS", "ada@example.invalid", RFC_SECRET))
                .isEqualTo("otpauth://totp/AI%20Career%20OS:ada%40example.invalid?secret=" + RFC_SECRET
                        + "&issuer=AI%20Career%20OS&algorithm=SHA1&digits=6&period=30");
    }
}
