package com.careeros.inbound.service;

import com.careeros.common.SignedLink;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Arrays;
import java.util.Base64;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/**
 * The address a recruiter's reply is forwarded to (roadmap 37.1).
 *
 * <p>It is the calendar feed's construction with one new constraint: a mailbox's local part is
 * capped at 64 octets (RFC 5321), and the calendar's token -- a whole UUID, a dot and a
 * 32-byte MAC -- is 80 characters before a domain joins it. So the account travels as its own
 * sixteen bytes and the signature as the first sixteen bytes of the same HMAC, base64url
 * without padding on both sides: 45 characters, 128 bits of forgery resistance, and the
 * address fits every provider's limit beside its domain.
 *
 * <p>The purpose keeps the three link families apart even though one secret signs all of them:
 * an unsubscribe URL cannot read letters, a calendar token cannot post one, and this token is
 * not a calendar subscription. Rotating {@code app.mail.link-secret} retires every address at
 * once, which is the answer to a forwarded letter.
 *
 * <p>{@code app.inbound.domain} is the provider's receiving domain. Empty means inbound mail
 * is not configured: the settings card says so and the webhook is a 404 like any other
 * unreadable address. A domain that is not a bare host, or one long enough to push the
 * address past the RFC's 254-octet line, stops the boot rather than handing out an address
 * that bounces.
 */
@Component
public class InboundLinks {

    /** The purpose this secret signs; a token signed for another surface is not valid here. */
    static final String PURPOSE = "careeros-inbound:";

    private static final int MAC_BYTES = 16;
    private static final int LOCAL_PART_LENGTH = 45;
    private static final int ADDRESS_MAX = 254;

    private final String secret;
    private final String domain;

    public InboundLinks(@Value("${app.mail.link-secret}") String secret,
                        @Value("${app.inbound.domain:}") String domain) {
        if (secret == null || secret.isBlank()) {
            throw new IllegalStateException(
                    "app.mail.link-secret is blank; it signs every inbound address a reader forwards to");
        }
        this.secret = secret;
        this.domain = domain == null ? "" : domain.trim();
        if (!this.domain.isEmpty() && !isHost(this.domain)) {
            throw new IllegalStateException(
                    "app.inbound.domain is not a bare host name: " + this.domain);
        }
        if (!this.domain.isEmpty() && LOCAL_PART_LENGTH + 1 + this.domain.length() > ADDRESS_MAX) {
            throw new IllegalStateException(
                    "app.inbound.domain is too long for an RFC 5321 address: " + this.domain);
        }
    }

    /** Whether this deployment can hand out an address at all. */
    public boolean configured() {
        return !domain.isEmpty();
    }

    /** The address the settings card shows; a deployment without a domain never gets here. */
    public String address(UUID userId) {
        if (!configured()) {
            throw new IllegalStateException("app.inbound.domain is not set");
        }
        return localPart(userId) + "@" + domain;
    }

    /**
     * The account this local part names, or null when it is unreadable, signed for another
     * account, signed with a secret that has since been rotated, or presented on a deployment
     * that has no receiving domain at all. Never throws: the value arrives from the open internet.
     */
    public UUID account(String localPart) {
        if (!configured() || localPart == null || localPart.isBlank()) {
            return null;
        }
        int dot = localPart.lastIndexOf('.');
        if (dot <= 0 || dot == localPart.length() - 1) {
            return null;
        }
        UUID id;
        byte[] presented;
        try {
            id = uuid(Base64.getUrlDecoder().decode(localPart.substring(0, dot)));
            presented = Base64.getUrlDecoder().decode(localPart.substring(dot + 1));
        } catch (IllegalArgumentException e) {
            return null;
        }
        byte[] expected = mac(id);
        return MessageDigest.isEqual(expected, presented) ? id : null;
    }

    /** The local part alone, so a test can hold it to the RFC's 64-octet cap. */
    String localPart(UUID userId) {
        return Base64.getUrlEncoder().withoutPadding().encodeToString(uuidBytes(userId))
                + "." + Base64.getUrlEncoder().withoutPadding().encodeToString(mac(userId));
    }

    private byte[] mac(UUID userId) {
        String whole = SignedLink.token(secret, PURPOSE, userId);
        byte[] signature = Base64.getUrlDecoder().decode(whole);
        return Arrays.copyOf(signature, MAC_BYTES);
    }

    private static byte[] uuidBytes(UUID id) {
        return ByteBuffer.allocate(16).putLong(id.getMostSignificantBits())
                .putLong(id.getLeastSignificantBits()).array();
    }

    private static UUID uuid(byte[] bytes) {
        if (bytes.length != 16) {
            throw new IllegalArgumentException("not a UUID");
        }
        ByteBuffer buffer = ByteBuffer.wrap(bytes);
        return new UUID(buffer.getLong(), buffer.getLong());
    }

    private static boolean isHost(String value) {
        if (value.length() > 253 || value.startsWith(".") || value.endsWith(".")) {
            return false;
        }
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            boolean legal = (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z')
                    || (c >= '0' && c <= '9') || c == '.' || c == '-';
            if (!legal) {
                return false;
            }
        }
        return value.getBytes(StandardCharsets.US_ASCII).length <= 253;
    }
}
