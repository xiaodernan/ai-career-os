package com.careeros.auth.service;

import java.util.Map;

/**
 * Outbound email port. {@code app.email.provider} chooses the transport: `console`
 * (the shipped default) logs the letter instead of sending it, and `smtp` hands it
 * to the relay named by `app.email.smtp.*`.
 *
 * <p>The header map is transport-level, not content: the letters use it for the
 * RFC 8058 unsubscribe pair, which a mailbox reads before the body is ever opened
 * (roadmap 23.1). A transport must carry the headers it is given -- a port that
 * silently dropped them would leave the letters looking unsubscribable while the
 * page they link to worked.
 */
public interface EmailSender {

    void send(String to, String subject, String body, Map<String, String> headers);

    /** A letter with no transport headers. */
    default void send(String to, String subject, String body) {
        send(to, subject, body, Map.of());
    }
}
