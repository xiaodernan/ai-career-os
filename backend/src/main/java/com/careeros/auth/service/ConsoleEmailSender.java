package com.careeros.auth.service;

import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Dev-only email transport: logs the message instead of sending it. `EmailConfig`
 * builds it when `app.email.provider` is `console`, the shipped default.
 *
 * <p>The body is withheld unless `app.email.console.log-body` is on: a reset mail
 * carries a link with a usable token, and a token belongs in a log file nobody meant
 * to trust only while someone is actively walking the flow. Transport headers are
 * held to the same rule -- the unsubscribe pair carries a signed link that changes
 * account settings -- so the default line names the headers and never prints them;
 * the dev toggle prints both. The dev compose turns the flag on; every other stack
 * keeps the default off.
 */
public class ConsoleEmailSender implements EmailSender {

    private static final Logger log = LoggerFactory.getLogger(ConsoleEmailSender.class);

    private final boolean logBody;

    public ConsoleEmailSender(boolean logBody) {
        this.logBody = logBody;
    }

    @Override
    public void send(String to, String subject, String body, Map<String, String> headers) {
        String headerNames = headers.isEmpty() ? "" : " headers=" + headers.keySet();
        if (logBody) {
            log.info("[email] to={} subject={}{}\n{}\n{}", to, subject, headerNames, headers, body);
        } else {
            log.info("[email] to={} subject={}{} body=(withheld; set app.email.console.log-body=true to print it)",
                    to, subject, headerNames);
        }
    }
}
