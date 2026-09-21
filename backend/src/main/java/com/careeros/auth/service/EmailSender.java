package com.careeros.auth.service;

/**
 * Outbound email port. The dev implementation logs to console; production should provide an
 * SMTP/transactional-email bean implementing this interface (e.g. via spring-boot-mail starter).
 */
public interface EmailSender {

    void send(String to, String subject, String body);
}
