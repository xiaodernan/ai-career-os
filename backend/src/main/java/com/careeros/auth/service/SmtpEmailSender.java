package com.careeros.auth.service;

import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;

/**
 * The production transport: hands one plain-text letter to the relay named by
 * {@code app.email.smtp.*}. `EmailConfig` builds it when {@code app.email.provider}
 * is `smtp`, and refuses to build it without a host and a from address.
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
    public void send(String to, String subject, String body) {
        SimpleMailMessage message = new SimpleMailMessage();
        message.setFrom(from);
        message.setTo(to);
        message.setSubject(subject);
        message.setText(body);
        mail.send(message);
    }
}
