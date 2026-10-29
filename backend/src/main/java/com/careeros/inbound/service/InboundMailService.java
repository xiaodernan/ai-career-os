package com.careeros.inbound.service;

import com.careeros.auth.repository.UserRepository;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.inbound.entity.InboundMail;
import com.careeros.inbound.repository.InboundMailRepository;
import com.careeros.inbound.web.InboundMailPayload;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Duration;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.HexFormat;
import java.util.Optional;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Receives one forwarded reply and keeps it (roadmap 37.1).
 *
 * <p>The token is the whole check: a valid one names an account that still exists, and every
 * other answer -- a forged signature, a retired secret, another surface's token, a deleted
 * account -- is the same 404 sentence, so the open internet cannot grade its guesses. The
 * caller is a mail provider, which retries a non-2xx; a duplicate is therefore acknowledged
 * with the same 200 rather than refused, and the unique (account, message key) pair is what
 * makes the second delivery the first letter.
 *
 * <p>What the letter keeps is what it said: sender, subject, text. Fields are trimmed and
 * capped rather than refused, because a provider retrying a 400 would retry forever and the
 * part beyond the cap is a footer, not the reply. An HTML body is never read: this product
 * does not render a stranger's markup. A payload with no sender, subject or text has no
 * letter in it and is acknowledged without a row.
 *
 * <p>The date is the letter's own when the payload carries one, clamped so a forged future
 * cannot pin the top of the reader's list. A date that cannot be read falls back to the
 * moment the webhook arrived, which is what a reader means by "received" anyway.
 */
@Service
public class InboundMailService {

    private static final Logger log = LoggerFactory.getLogger(InboundMailService.class);

    private static final int FROM_MAX = 320;
    private static final int SUBJECT_MAX = 500;
    private static final int BODY_MAX = 20_000;
    private static final int KEY_MAX = 256;
    private static final Duration FUTURE_SKEW = Duration.ofHours(24);

    private final InboundLinks links;
    private final InboundMailRepository mails;
    private final UserRepository users;

    public InboundMailService(InboundLinks links, InboundMailRepository mails, UserRepository users) {
        this.links = links;
        this.mails = mails;
        this.users = users;
    }

    /** One delivery's outcome: the row it names, and whether this call was a retry. */
    public record Received(UUID id, boolean duplicate) {
    }

    @Transactional
    public Received receive(String token, InboundMailPayload payload) {
        UUID userId = links.account(token);
        if (userId == null || users.findById(userId).isEmpty()) {
            throw new ApiException(ApiErrorCode.INBOUND_LINK_INVALID,
                    "This inbound address is not valid or has been retired");
        }

        String from = cap(trim(payload.from()), FROM_MAX);
        String subject = cap(trim(payload.subject()), SUBJECT_MAX);
        String body = cap(trim(payload.textBody()), BODY_MAX);
        if (from.isEmpty() && subject.isEmpty() && body.isEmpty()) {
            return new Received(null, false);
        }

        String key = key(payload, from, subject, body);
        Optional<InboundMail> seen = mails.findByUserIdAndMessageKey(userId, key);
        if (seen.isPresent()) {
            return new Received(seen.get().getId(), true);
        }

        InboundMail mail = new InboundMail();
        mail.setUserId(userId);
        mail.setMessageKey(key);
        mail.setFromAddress(from);
        mail.setSubject(subject);
        mail.setBodyText(body);
        mail.setReceivedAt(receivedAt(payload.date()));
        mails.save(mail);
        log.info("Inbound mail {} received for user {}", mail.getId(), userId);
        return new Received(mail.getId(), false);
    }

    private static String key(InboundMailPayload payload, String from, String subject, String body) {
        String named = trim(payload.messageId());
        if (!named.isEmpty()) {
            return cap(named, KEY_MAX);
        }
        return sha256(from + "\n" + subject + "\n" + trim(payload.date()) + "\n" + body);
    }

    /**
     * The letter's date, or now when it has none this server can read. A date more than a day
     * ahead is not a letter from the future; it is a forged clock, and the answer is the
     * moment the delivery arrived.
     */
    static OffsetDateTime receivedAt(String value) {
        OffsetDateTime now = OffsetDateTime.now(ZoneOffset.UTC);
        String text = trim(value);
        if (text.isEmpty()) {
            return now;
        }
        OffsetDateTime parsed = parse(text);
        if (parsed == null) {
            return now;
        }
        return parsed.isAfter(now.plus(FUTURE_SKEW)) ? now : parsed;
    }

    private static OffsetDateTime parse(String text) {
        try {
            return OffsetDateTime.parse(text);
        } catch (DateTimeParseException ignored) {
            // Not ISO; try the mail standard below.
        }
        try {
            return ZonedDateTime.parse(text, DateTimeFormatter.RFC_1123_DATE_TIME).toOffsetDateTime();
        } catch (DateTimeParseException ignored) {
            return null;
        }
    }

    private static String trim(String value) {
        return value == null ? "" : value.strip();
    }

    /** Cut to the column's size without splitting a surrogate pair. */
    private static String cap(String value, int max) {
        if (value.length() <= max) {
            return value;
        }
        int end = max;
        if (Character.isHighSurrogate(value.charAt(end - 1))) {
            end--;
        }
        return value.substring(0, end);
    }

    private static String sha256(String value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return HexFormat.of().formatHex(digest.digest(value.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 is unavailable", e);
        }
    }
}
