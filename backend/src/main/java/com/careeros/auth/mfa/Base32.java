package com.careeros.auth.mfa;

import java.io.ByteArrayOutputStream;
import java.util.Locale;

/**
 * RFC 4648's base32, uppercase and unpadded -- the spelling every authenticator app reads from
 * an {@code otpauth://} URI.
 *
 * <p>Hand-written rather than pulled from a dependency: the alphabet is thirty-two characters
 * and the encode/decode pair is a dozen lines, while a new jar in the backend is a new thing to
 * audit and pin. Decoding accepts what a reader's keyboard or a pasted QR payload may carry --
 * lowercase, spaces, hyphens, trailing padding -- because every one of those is the same seed.
 */
public final class Base32 {

    private static final String ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";

    private Base32() {
    }

    public static String encode(byte[] data) {
        StringBuilder out = new StringBuilder((data.length * 8 + 4) / 5);
        int buffer = 0;
        int bits = 0;
        for (byte value : data) {
            buffer = (buffer << 8) | (value & 0xFF);
            bits += 8;
            while (bits >= 5) {
                out.append(ALPHABET.charAt((buffer >> (bits - 5)) & 0x1F));
                bits -= 5;
            }
        }
        if (bits > 0) {
            out.append(ALPHABET.charAt((buffer << (5 - bits)) & 0x1F));
        }
        return out.toString();
    }

    /** Returns the bytes the text spells; throws {@link IllegalArgumentException} on any other character. */
    public static byte[] decode(String text) {
        String cleaned = text.trim().replace(" ", "").replace("-", "").replace("=", "")
                .toUpperCase(Locale.ROOT);
        if (cleaned.isEmpty()) {
            throw new IllegalArgumentException("empty base32 text");
        }
        ByteArrayOutputStream out = new ByteArrayOutputStream(cleaned.length() * 5 / 8);
        int buffer = 0;
        int bits = 0;
        for (int index = 0; index < cleaned.length(); index++) {
            int value = ALPHABET.indexOf(cleaned.charAt(index));
            if (value < 0) {
                throw new IllegalArgumentException("not a base32 character: " + cleaned.charAt(index));
            }
            buffer = (buffer << 5) | value;
            bits += 5;
            if (bits >= 8) {
                out.write((buffer >> (bits - 8)) & 0xFF);
                bits -= 8;
            }
        }
        return out.toByteArray();
    }
}
