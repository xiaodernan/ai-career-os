package com.careeros.auth.mfa;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.time.Instant;
import java.util.Locale;
import java.util.OptionalLong;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

/**
 * Time-based one-time passwords (RFC 6238) over the HMAC-SHA1 defaults every authenticator app
 * implements: 30-second steps, six digits, a twenty-byte seed. The parameters are constants
 * rather than settings because the account's phone has already been told what they are by the
 * {@code otpauth://} URI -- a server that let them drift would verify nothing the phone shows.
 *
 * <p>The accepted window is the current step plus one either side, which is what RFC 6238 §5.2
 * allows for clocks that are not perfectly aligned. The window is also where replay lives: a
 * code verified at step {@code n} must be refused when presented again during the same step,
 * so {@link #match} answers with the step it matched and the caller remembers the highest one
 * it has spent.
 *
 * <p>Comparison goes through {@link MessageDigest#isEqual} and every candidate step in the
 * window is computed even after a match: an early exit would time the answer by its position
 * in the window, and a wrong code should cost the same as a right one.
 */
public final class Totp {

    public static final int STEP_SECONDS = 30;
    public static final int DIGITS = 6;
    public static final int DEFAULT_SKEW_STEPS = 1;

    /** RFC 4226 §4 recommends 160 bits for HMAC-SHA1; twenty bytes is the universal seed size. */
    private static final int SECRET_BYTES = 20;

    private static final SecureRandom RANDOM = new SecureRandom();

    private Totp() {
    }

    /** A fresh 160-bit seed, spelled the way the URI and the authenticator expect it. */
    public static String newSecret() {
        byte[] seed = new byte[SECRET_BYTES];
        RANDOM.nextBytes(seed);
        return Base32.encode(seed);
    }

    public static long stepAt(Instant at) {
        return Math.floorDiv(at.getEpochSecond(), STEP_SECONDS);
    }

    public static String code(String base32Secret, long step) {
        return code(Base32.decode(base32Secret), step);
    }

    public static String code(byte[] secret, long step) {
        byte[] hash = hmac(secret, step);
        int offset = hash[hash.length - 1] & 0x0F;
        int binary = ((hash[offset] & 0x7F) << 24)
                | ((hash[offset + 1] & 0xFF) << 16)
                | ((hash[offset + 2] & 0xFF) << 8)
                | (hash[offset + 3] & 0xFF);
        return String.format(Locale.ROOT, "%0" + DIGITS + "d", binary % 1_000_000);
    }

    /**
     * The step {@code presented} answers for, or empty when it is not this seed's code in the
     * window around {@code at}. When two steps in the window happen to match (a 3-in-a-million
     * coincidence), the highest is returned so the replay guard's mark only moves forward.
     */
    public static OptionalLong match(String base32Secret, String presented, Instant at, int skewSteps) {
        if (presented == null) {
            return OptionalLong.empty();
        }
        String candidate = presented.trim().replace(" ", "");
        if (candidate.length() != DIGITS || !candidate.chars().allMatch(Character::isDigit)) {
            return OptionalLong.empty();
        }
        byte[] secret = Base32.decode(base32Secret);
        byte[] presentedBytes = candidate.getBytes(StandardCharsets.US_ASCII);
        long now = stepAt(at);
        long matched = Long.MIN_VALUE;
        for (long step = now - skewSteps; step <= now + skewSteps; step++) {
            byte[] expected = code(secret, step).getBytes(StandardCharsets.US_ASCII);
            if (MessageDigest.isEqual(expected, presentedBytes)) {
                matched = Math.max(matched, step);
            }
        }
        return matched == Long.MIN_VALUE ? OptionalLong.empty() : OptionalLong.of(matched);
    }

    /** The URI an authenticator app scans or a reader types; the label is what its list shows. */
    public static String otpauthUri(String issuer, String account, String base32Secret) {
        String label = urlEncode(issuer) + ":" + urlEncode(account);
        return "otpauth://totp/" + label
                + "?secret=" + base32Secret
                + "&issuer=" + urlEncode(issuer)
                + "&algorithm=SHA1"
                + "&digits=" + DIGITS
                + "&period=" + STEP_SECONDS;
    }

    private static byte[] hmac(byte[] secret, long step) {
        byte[] counter = new byte[8];
        long value = step;
        for (int index = 7; index >= 0; index--) {
            counter[index] = (byte) (value & 0xFF);
            value >>>= 8;
        }
        try {
            Mac mac = Mac.getInstance("HmacSHA1");
            mac.init(new SecretKeySpec(secret, "HmacSHA1"));
            return mac.doFinal(counter);
        } catch (java.security.GeneralSecurityException e) {
            throw new IllegalStateException("HmacSHA1 is required by RFC 6238 and missing here", e);
        }
    }

    /** Percent-encoding with %20 for spaces: the form a URI's query and label accept. */
    private static String urlEncode(String value) {
        return java.net.URLEncoder.encode(value, StandardCharsets.UTF_8).replace("+", "%20");
    }
}
