package com.careeros.auth.service;

import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.read.ListAppender;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.slf4j.LoggerFactory;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The console transport is the one place a usable reset token could reach the
 * logs, so its default behavior is pinned here: subject and recipient are
 * logged, the body (which carries the token link) is not, and only the explicit
 * dev toggle prints it.
 */
class ConsoleEmailSenderTest {

    private static final String BODY = "Open <http://localhost:3000/reset-password?token=secret-token> to continue";
    private static final Logger LOGGER = (Logger) LoggerFactory.getLogger(ConsoleEmailSender.class);

    private ListAppender<ILoggingEvent> appender;

    @BeforeEach
    void attach() {
        appender = new ListAppender<>();
        appender.start();
        LOGGER.addAppender(appender);
    }

    @AfterEach
    void detach() {
        LOGGER.detachAppender(appender);
    }

    private String soleMessage(ConsoleEmailSender sender) {
        sender.send("a@example.com", "Reset your password", BODY);
        assertThat(appender.list).hasSize(1);
        return appender.list.get(0).getFormattedMessage();
    }

    @Test
    void the_body_is_withheld_by_default_so_the_token_never_reaches_the_log() {
        String line = soleMessage(new ConsoleEmailSender(false));

        assertThat(line).contains("a@example.com", "Reset your password").doesNotContain("secret-token");
    }

    @Test
    void the_dev_toggle_prints_the_body_so_the_local_flow_can_be_walked() {
        String line = soleMessage(new ConsoleEmailSender(true));

        assertThat(line).contains("secret-token");
    }
}
