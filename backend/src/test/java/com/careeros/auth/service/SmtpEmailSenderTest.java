package com.careeros.auth.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import jakarta.mail.Session;
import jakarta.mail.internet.MimeMessage;
import jakarta.mail.internet.MimeUtility;
import java.util.Map;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.mail.MailSendException;
import org.springframework.mail.javamail.JavaMailSender;

/**
 * The SMTP transport (roadmap 21.1, 23.1). What it owes the rest of the app is one plain
 * letter with the configured sender, the transport headers it was handed, and a failure that
 * travels: the reset flow believes a send that returns, so a swallowed relay error would be a
 * caller waiting for mail that never left.
 *
 * <p>The letter is a MIME message rather than a {@code SimpleMailMessage} because the letters
 * carry the RFC 8058 unsubscribe pair and because the account's language puts non-ASCII into
 * subjects and bodies. Both are pinned here: a header the transport dropped would make a
 * letter look unsubscribable, and a subject mangled at the relay would be a Chinese reader
 * receiving English-looking noise.
 */
class SmtpEmailSenderTest {

    private final JavaMailSender mail = mock(JavaMailSender.class);
    private final SmtpEmailSender sender = new SmtpEmailSender(mail, "careeros@example.com");

    @BeforeEach
    void handOutAMessage() {
        when(mail.createMimeMessage()).thenReturn(new MimeMessage((Session) null));
    }

    @Test
    void a_letter_is_handed_to_the_relay_with_the_configured_sender() throws Exception {
        sender.send("ada@example.com", "Reset your AI Career OS password", "Open the link");

        MimeMessage sent = capture();
        assertThat(sent.getFrom()[0].toString()).isEqualTo("careeros@example.com");
        assertThat(sent.getAllRecipients()[0].toString()).isEqualTo("ada@example.com");
        assertThat(MimeUtility.decodeText(sent.getSubject()))
                .isEqualTo("Reset your AI Career OS password");
        assertThat(sent.getContent()).isEqualTo("Open the link");
    }

    @Test
    void the_headers_the_letter_carries_reach_the_relay() throws Exception {
        sender.send("ada@example.com", "Your week", "Body",
                Map.of("List-Unsubscribe", "<https://careeros.example/stop/1>",
                        "List-Unsubscribe-Post", "List-Unsubscribe=One-Click"));

        MimeMessage sent = capture();
        assertThat(sent.getHeader("List-Unsubscribe")[0])
                .isEqualTo("<https://careeros.example/stop/1>");
        assertThat(sent.getHeader("List-Unsubscribe-Post")[0])
                .isEqualTo("List-Unsubscribe=One-Click");
    }

    @Test
    void a_chinese_subject_and_body_survive_the_encoding() throws Exception {
        sender.send("ada@example.com", "你的求职周报（26 Oct 2026）", "这一周没有新的投递。");

        MimeMessage sent = capture();
        assertThat(MimeUtility.decodeText(sent.getSubject()))
                .isEqualTo("你的求职周报（26 Oct 2026）");
        assertThat(sent.getContent()).isEqualTo("这一周没有新的投递。");
    }

    @Test
    void a_relay_that_refuses_the_letter_says_so_instead_of_swallowing_it() {
        doThrow(new MailSendException("relay said 550"))
                .when(mail).send(any(MimeMessage.class));

        assertThatThrownBy(() -> sender.send("ada@example.com", "Reset", "Open the link"))
                .isInstanceOf(MailSendException.class)
                .hasMessageContaining("550");
    }

    private MimeMessage capture() {
        ArgumentCaptor<MimeMessage> sent = ArgumentCaptor.forClass(MimeMessage.class);
        verify(mail).send(sent.capture());
        return sent.getValue();
    }
}
