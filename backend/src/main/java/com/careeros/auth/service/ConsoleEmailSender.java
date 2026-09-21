package com.careeros.auth.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

/** Dev-only email transport: logs the message instead of sending it. Replace per EmailSender contract. */
@Component
public class ConsoleEmailSender implements EmailSender {

    private static final Logger log = LoggerFactory.getLogger(ConsoleEmailSender.class);

    @Override
    public void send(String to, String subject, String body) {
        log.info("[email] to={} subject={}\n{}", to, subject, body);
    }
}
