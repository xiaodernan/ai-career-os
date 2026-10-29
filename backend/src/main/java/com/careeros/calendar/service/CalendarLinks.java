package com.careeros.calendar.service;

import com.careeros.common.SignedLink;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/**
 * The one address a calendar client subscribes to (roadmap 34).
 *
 * <p>A calendar client keeps fetching a URL that it stores once, from a server the reader
 * never signs in on. So the URL is the credential: the token carries the account id and an
 * HMAC over it with a purpose of its own, and rotating {@code app.mail.link-secret} retires
 * every feed ever issued -- the same answer to a forwarded URL that the mail links give.
 * The purpose is separate from the mail-preference one so an unsubscribe link pasted into a
 * calendar app reads nothing, even though both are signed with the same key.
 *
 * <p>The address is absolute and built from {@code app.web.base-url} for the same reason the
 * letters are: the reader pastes it from the screen, and the deployment's public origin is
 * where both the shell and the API answer.
 */
@Component
public class CalendarLinks {

    /** The purposes this secret signs; a token signed for one surface is not valid on another. */
    static final String PURPOSE = "careeros-calendar:";

    private static final String PATH = "/api/v1/calendar.ics?token=";

    private final String secret;
    private final String baseUrl;

    public CalendarLinks(@Value("${app.mail.link-secret}") String secret,
                         @Value("${app.web.base-url:http://localhost:3000}") String baseUrl) {
        if (secret == null || secret.isBlank()) {
            throw new IllegalStateException(
                    "app.mail.link-secret is blank; it signs every calendar feed a reader subscribes to");
        }
        this.secret = secret;
        this.baseUrl = baseUrl.endsWith("/") ? baseUrl.substring(0, baseUrl.length() - 1) : baseUrl;
    }

    /** The subscription address, whole: a calendar client has no app to resolve a path against. */
    public String feed(UUID userId) {
        return baseUrl + PATH + token(userId);
    }

    /** The reader-facing origin, for the event links that point back into the app. */
    public String webRoot() {
        return baseUrl;
    }

    /** The account id plus its signature, one opaque value a calendar subscription stores verbatim. */
    public String token(UUID userId) {
        return userId + "." + SignedLink.token(secret, PURPOSE, userId);
    }

    /**
     * The account this token names, or null when the token is unreadable, signed for another
     * account, or signed with a secret that has since been rotated. Never throws: the value
     * arrives from the open internet.
     */
    public UUID account(String token) {
        if (token == null || token.isBlank()) {
            return null;
        }
        int dot = token.lastIndexOf('.');
        if (dot <= 0 || dot == token.length() - 1) {
            return null;
        }
        UUID id;
        try {
            id = UUID.fromString(token.substring(0, dot));
        } catch (IllegalArgumentException e) {
            return null;
        }
        return SignedLink.valid(secret, PURPOSE, id, token.substring(dot + 1)) ? id : null;
    }
}
