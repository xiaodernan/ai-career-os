package com.careeros.common;

import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.MessageDigest;
import java.util.Base64;
import java.util.UUID;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

/**
 * The signature under a link that is its own credential (roadmap 23.1 and 34).
 *
 * <p>A mailbox and a calendar client can carry neither a bearer token nor a login, so the
 * account id and a signature travel in the URL. The signature is an HMAC over a purpose and
 * the account id, with a key that never leaves the server, compared in constant time: a
 * reader can shorten a link, not forge one. The purpose is what keeps one kind of link from
 * working as another -- the signature under an unsubscribe URL is not the signature under a
 * calendar feed, even when both name the same account and the same secret.
 *
 * <p>Nothing is stored per link, so rotating the secret retires every link ever issued at
 * once. That is the intended response to a leak and the reason each surface prints the
 * warning next to the URL.
 */
public final class SignedLink {

    private static final String ALGORITHM = "HmacSHA256";

    private SignedLink() {
    }

    /**
     * The URL-safe, unpadded signature for one account and one purpose. Deterministic, so a
     * re-issued link works without storing anything.
     */
    public static String token(String secret, String purpose, UUID userId) {
        try {
            Mac mac = Mac.getInstance(ALGORITHM);
            mac.init(new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8), ALGORITHM));
            byte[] signature = mac.doFinal((purpose + userId).getBytes(StandardCharsets.UTF_8));
            return Base64.getUrlEncoder().withoutPadding().encodeToString(signature);
        } catch (GeneralSecurityException e) {
            throw new IllegalStateException("HMAC-SHA256 is unavailable", e);
        }
    }

    /**
     * Whether the token is this account's. Constant-time over the MAC so a wrong signature
     * costs the same as a right one; a malformed token is false, never an exception, because
     * it arrives from the open internet.
     */
    public static boolean valid(String secret, String purpose, UUID userId, String token) {
        if (token == null || token.isBlank()) {
            return false;
        }
        byte[] presented;
        try {
            presented = Base64.getUrlDecoder().decode(token);
        } catch (IllegalArgumentException e) {
            return false;
        }
        byte[] expected = Base64.getUrlDecoder().decode(token(secret, purpose, userId));
        return MessageDigest.isEqual(expected, presented);
    }
}
