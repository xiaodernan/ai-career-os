package com.careeros.auth.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.mail.MailSendException;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;

/**
 * The SMTP transport (roadmap 21.1). What it owes the rest of the app is one plain
 * letter with the configured sender, and a failure that travels: the reset flow
 * believes a send that returns, so a swallowed relay error would be a caller waiting
 * for mail that never left.
 */
class SmtpEmailSenderTest {

    private final JavaMailSender mail = mock(JavaMailSender.class);
    private final SmtpEmailSender sender = new SmtpEmailSender(mail, "careeros@example.com");

    @Test
    void a_letter_is_handed_to_the_relay_with_the_configured_sender() {
        sender.send("ada@example.com", "Reset your AI Career OS password", "Open the link");

        ArgumentCaptor<SimpleMailMessage> sent = ArgumentCaptor.forClass(SimpleMailMessage.class);
        verify(mail).send(sent.capture());
        assertThat(sent.getValue().getFrom()).isEqualTo("careeros@example.com");
        assertThat(sent.getValue().getTo()).containsExactly("ada@example.com");
        assertThat(sent.getValue().getSubject()).isEqualTo("Reset your AI Career OS password");
        assertThat(sent.getValue().getText()).isEqualTo("Open the link");
    }

    @Test
    void a_relay_that_refuses_the_letter_says_so_instead_of_swallowing_it() {
        doThrow(new MailSendException("relay said 550"))
                .when(mail).send(any(SimpleMailMessage.class));

        assertThatThrownBy(() -> sender.send("ada@example.com", "Reset", "Open the link"))
                .isInstanceOf(MailSendException.class)
                .hasMessageContaining("550");
    }
}
