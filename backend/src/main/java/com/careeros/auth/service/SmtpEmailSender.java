package com.careeros.auth.service;

import jakarta.mail.MessagingException;
import jakarta.mail.internet.MimeMessage;
import java.util.Map;
import org.springframework.mail.MailSendException;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.mail.javamail.MimeMessageHelper;

/**
 * The production transport: hands one plain-text letter to the relay named by
 * {@code app.email.smtp.*}. `EmailConfig` builds it when {@code app.email.provider}
 * is `smtp`, and refuses to build it without a host and a from address.
 *
 * <p>The message is a MIME one rather than a {@code SimpleMailMessage} because the
 * letters carry transport headers now (roadmap 23.1) and because the account's own
 * language puts non-ASCII into subjects and bodies: the helper writes both as UTF-8,
 * where the simpler message left the encoding to the relay's defaults.
 *
 * <p>A relay failure is thrown, not logged away: a password reset the caller believes
 * was mailed but was not is worse than a request that says the mail could not leave.
 */
public class SmtpEmailSender implements EmailSender {

    private final JavaMailSender mail;
    private final String from;

    public SmtpEmailSender(JavaMailSender mail, String from) {
        this.mail = mail;
        this.from = from;
    }

    @Override
    public void send(String to, String subject, String body, Map<String, String> headers) {
        MimeMessage message = mail.createMimeMessage();
        try {
            MimeMessageHelper helper = new MimeMessageHelper(message, false, "UTF-8");
            helper.setFrom(from);
            helper.setTo(to);
            helper.setSubject(subject);
            helper.setText(body, false);
            for (Map.Entry<String, String> header : headers.entrySet()) {
                message.setHeader(header.getKey(), header.getValue());
            }
        } catch (MessagingException e) {
            throw new MailSendException("the letter could not be prepared for the relay", e);
        }
        mail.send(message);
    }
}
