package com.careeros.config;

import com.careeros.auth.service.ConsoleEmailSender;
import com.careeros.auth.service.EmailSender;
import com.careeros.auth.service.SmtpEmailSender;
import java.util.Locale;
import java.util.Properties;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.mail.javamail.JavaMailSenderImpl;

/**
 * The one outbound-mail bean, chosen by {@code app.email.provider}. The switch is
 * resolved here rather than with two conditional beans so an unknown provider is a
 * boot that names it instead of a context with no mail transport at all.
 *
 * <p>`smtp` refuses to start without a host and a from address: a relay that cannot
 * be reached is a request that fails, but a missing sender address is every letter
 * refused at the relay, one at a time, long after the boot looked fine.
 */
@Configuration
public class EmailConfig {

    /** A dead relay must not hold a request open; the Redis client got the same 5 s. */
    static final String SMTP_TIMEOUT_MS = "5000";

    @Bean
    EmailSender emailSender(
            @Value("${app.email.provider}") String provider,
            @Value("${app.email.from:}") String from,
            @Value("${app.email.console.log-body:false}") boolean logBody,
            @Value("${app.email.smtp.host:}") String host,
            @Value("${app.email.smtp.port:587}") int port,
            @Value("${app.email.smtp.username:}") String username,
            @Value("${app.email.smtp.password:}") String password,
            @Value("${app.email.smtp.starttls:true}") boolean starttls,
            @Value("${app.email.smtp.ssl:false}") boolean ssl) {
        String chosen = provider.trim().toLowerCase(Locale.ROOT);
        return switch (chosen) {
            case "console" -> new ConsoleEmailSender(logBody);
            case "smtp" -> {
                require(from, "app.email.from", "the address the relay sends as");
                require(host, "app.email.smtp.host", "the relay to hand mail to");
                if (starttls && ssl) {
                    throw new IllegalStateException("app.email.smtp.starttls and app.email.smtp.ssl "
                            + "cannot both be true: 587 upgrades with STARTTLS, 465 is TLS from the first byte");
                }
                yield new SmtpEmailSender(
                        relay(host.trim(), port, username.trim(), password, starttls, ssl), from.trim());
            }
            default -> throw new IllegalStateException("app.email.provider is '" + provider
                    + "'; it must be console or smtp");
        };
    }

    private static void require(String value, String property, String what) {
        if (value == null || value.isBlank()) {
            throw new IllegalStateException("app.email.provider=smtp needs " + property + ", " + what);
        }
    }

    static JavaMailSenderImpl relay(String host, int port, String username, String password,
            boolean starttls, boolean ssl) {
        JavaMailSenderImpl mail = new JavaMailSenderImpl();
        mail.setHost(host);
        mail.setPort(port);
        boolean authenticated = !username.isBlank();
        if (authenticated) {
            mail.setUsername(username);
            mail.setPassword(password);
        }
        Properties props = mail.getJavaMailProperties();
        props.put("mail.smtp.auth", Boolean.toString(authenticated));
        props.put("mail.smtp.starttls.enable", Boolean.toString(starttls));
        props.put("mail.smtp.ssl.enable", Boolean.toString(ssl));
        props.put("mail.smtp.connectiontimeout", SMTP_TIMEOUT_MS);
        props.put("mail.smtp.timeout", SMTP_TIMEOUT_MS);
        props.put("mail.smtp.writetimeout", SMTP_TIMEOUT_MS);
        return mail;
    }
}
