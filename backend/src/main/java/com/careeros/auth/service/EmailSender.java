package com.careeros.auth.service;

/**
 * Outbound email port. {@code app.email.provider} chooses the transport: `console`
 * (the shipped default) logs the letter instead of sending it, and `smtp` hands it
 * to the relay named by {@code app.email.smtp.*}.
 */
public interface EmailSender {

    void send(String to, String subject, String body);
}
