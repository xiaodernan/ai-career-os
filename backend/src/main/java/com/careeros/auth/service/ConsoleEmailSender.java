package com.careeros.auth.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Dev-only email transport: logs the message instead of sending it. `EmailConfig`
 * builds it when {@code app.email.provider} is `console`, the shipped default.
 *
 * <p>The body is withheld unless {@code app.email.console.log-body} is on: a
 * reset mail carries a link with a usable token, and a token belongs in a log
 * file nobody meant to trust only while someone is actively walking the flow.
 * The dev compose turns the flag on; every other stack keeps the default off.
 */
public class ConsoleEmailSender implements EmailSender {

    private static final Logger log = LoggerFactory.getLogger(ConsoleEmailSender.class);

    private final boolean logBody;

    public ConsoleEmailSender(boolean logBody) {
        this.logBody = logBody;
    }

    @Override
    public void send(String to, String subject, String body) {
        if (logBody) {
            log.info("[email] to={} subject={}\n{}", to, subject, body);
        } else {
            log.info("[email] to={} subject={} body=(withheld; set app.email.console.log-body=true to print it)",
                    to, subject);
        }
    }
}
