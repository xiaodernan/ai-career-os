package com.careeros.mail.service;

import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.MessageDigest;
import java.util.Base64;
import java.util.Map;
import java.util.UUID;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/**
 * The links the letters carry back (roadmap 23.1): one page that shows the two dials, and one
 * POST URL per letter that a mail client can fire without a browser.
 *
 * <p>A mailbox cannot send a bearer token and should not have to log in to stop mail, so the
 * account id and a signature travel in the URL. The signature is an HMAC over the account id
 * with a key that never leaves the server, compared in constant time: a reader can shorten a
 * link, not forge one, and the page has no way to change anyone else's settings. Nothing is
 * stored per link -- rotating {@code app.mail.link-secret} retires every link ever mailed,
 * which is the intended response to a leak and the reason the page prints that warning.
 *
 * <p>Both URLs are absolute because a mailbox has no browser history to resolve a path
 * against, and both are built from {@code app.web.base-url}: the mail arrives from the
 * backend, but the reader's origin is the app that proxies it, so the link points there.
 */
@Component
public class MailLinks {

    /** The header names of RFC 8058's one-click unsubscribe; Gmail and Yahoo read these. */
    static final String LIST_UNSUBSCRIBE = "List-Unsubscribe";
    static final String LIST_UNSUBSCRIBE_POST = "List-Unsubscribe-Post";

    private static final String ALGORITHM = "HmacSHA256";
    private static final String PREFIX = "careeros-mail-preference:";

    private final String secret;
    private final String baseUrl;

    public MailLinks(@Value("${app.mail.link-secret}") String secret,
                     @Value("${app.web.base-url:http://localhost:3000}") String baseUrl) {
        if (secret == null || secret.isBlank()) {
            throw new IllegalStateException(
                    "app.mail.link-secret is blank; it signs every unsubscribe link a letter carries");
        }
        this.secret = secret;
        this.baseUrl = baseUrl.endsWith("/") ? baseUrl.substring(0, baseUrl.length() - 1) : baseUrl;
    }

    /** The page both letters link to: the state of both dials, with the buttons that change it. */
    public String page(UUID userId) {
        return root() + "/" + userId + "/" + token(userId);
    }

    /** The reader-facing origin, for links that point at screens rather than at this page. */
    public String webRoot() {
        return baseUrl;
    }

    /** The POST a mail client fires for one-click unsubscribe; a GET here must change nothing. */
    public String stop(UUID userId, MailList list) {
        return page(userId) + "/stop/" + list.slug();
    }

    /** The POST the page's "turn it back on" button fires. */
    public String start(UUID userId, MailList list) {
        return page(userId) + "/start/" + list.slug();
    }

    /** The per-account signature, URL-safe and unpadded so a mail client never re-encodes it. */
    public String token(UUID userId) {
        try {
            Mac mac = Mac.getInstance(ALGORITHM);
            mac.init(new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8), ALGORITHM));
            byte[] signature = mac.doFinal((PREFIX + userId).getBytes(StandardCharsets.UTF_8));
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
    public boolean valid(UUID userId, String token) {
        if (token == null || token.isBlank()) {
            return false;
        }
        byte[] presented;
        try {
            presented = Base64.getUrlDecoder().decode(token);
        } catch (IllegalArgumentException e) {
            return false;
        }
        byte[] expected = Base64.getUrlDecoder().decode(token(userId));
        return MessageDigest.isEqual(expected, presented);
    }

    /**
     * The headers that let a mail client offer "unsubscribe" beside the sender name and settle
     * it without the reader opening anything. The POST body RFC 8058 prescribes is not read by
     * the endpoint: the URL already names the list, and a GET on it changes nothing.
     */
    public Map<String, String> oneClick(UUID userId, MailList list) {
        return Map.of(
                LIST_UNSUBSCRIBE, "<" + stop(userId, list) + ">",
                LIST_UNSUBSCRIBE_POST, "List-Unsubscribe=One-Click");
    }

    private String root() {
        return baseUrl + "/api/v1/mail/preferences";
    }
}
