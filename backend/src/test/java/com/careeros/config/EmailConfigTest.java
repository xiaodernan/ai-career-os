package com.careeros.config;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.careeros.auth.service.ConsoleEmailSender;
import com.careeros.auth.service.EmailSender;
import com.careeros.auth.service.SmtpEmailSender;
import java.util.Properties;
import org.junit.jupiter.api.Test;
import org.springframework.mail.javamail.JavaMailSenderImpl;

/**
 * The transport switch (roadmap 21.1). The shipped default must stay the console
 * transport — a deployment that never configured mail keeps logging it — and `smtp`
 * must fail at boot, by name, when it cannot possibly work: a missing host or sender
 * address otherwise shows up as every letter failing at the relay after the boot
 * looked fine.
 */
class EmailConfigTest {

    private final EmailConfig config = new EmailConfig();

    private EmailSender chosen(String provider, String from, boolean logBody, String host, int port,
            String username, String password, boolean starttls, boolean ssl) {
        return config.emailSender(provider, from, logBody, host, port, username, password, starttls, ssl);
    }

    @Test
    void console_is_the_default_and_keeps_the_body_behind_the_dev_toggle() {
        assertThat(chosen("console", "", false, "", 587, "", "", true, false))
                .isInstanceOf(ConsoleEmailSender.class);
        assertThat(chosen(" CONSOLE ", "", true, "", 587, "", "", true, false))
                .isInstanceOf(ConsoleEmailSender.class);
    }

    @Test
    void a_provider_that_is_neither_console_nor_smtp_refuses_to_boot_naming_itself() {
        assertThatThrownBy(() -> chosen("relay", "careeros@example.com", false, "smtp.example.com",
                587, "", "", true, false))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("relay")
                .hasMessageContaining("console or smtp");
    }

    @Test
    void smtp_without_a_host_names_the_property_it_needs() {
        assertThatThrownBy(() -> chosen("smtp", "careeros@example.com", false, " ", 587, "", "", true, false))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("app.email.smtp.host");
    }

    @Test
    void smtp_without_a_sender_address_names_the_property_it_needs() {
        assertThatThrownBy(() -> chosen("smtp", "", false, "smtp.example.com", 587, "", "", true, false))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("app.email.from");
    }

    @Test
    void starttls_and_ssl_together_are_refused_rather_than_guessed() {
        assertThatThrownBy(() -> chosen("smtp", "careeros@example.com", false, "smtp.example.com",
                587, "", "", true, true))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("cannot both be true");
    }

    @Test
    void smtp_is_chosen_when_the_provider_says_so() {
        assertThat(chosen("smtp", "careeros@example.com", false, "smtp.example.com",
                2525, "ada", "secret", true, false))
                .isInstanceOf(SmtpEmailSender.class);
    }

    @Test
    void the_relay_carries_the_settings_and_the_five_second_ceilings() {
        JavaMailSenderImpl relay = EmailConfig.relay("smtp.example.com", 2525, "ada", "secret", true, false);

        assertThat(relay.getHost()).isEqualTo("smtp.example.com");
        assertThat(relay.getPort()).isEqualTo(2525);
        assertThat(relay.getUsername()).isEqualTo("ada");
        assertThat(relay.getPassword()).isEqualTo("secret");
        Properties props = relay.getJavaMailProperties();
        assertThat(props)
                .containsEntry("mail.smtp.auth", "true")
                .containsEntry("mail.smtp.starttls.enable", "true")
                .containsEntry("mail.smtp.ssl.enable", "false")
                .containsEntry("mail.smtp.connectiontimeout", EmailConfig.SMTP_TIMEOUT_MS)
                .containsEntry("mail.smtp.timeout", EmailConfig.SMTP_TIMEOUT_MS)
                .containsEntry("mail.smtp.writetimeout", EmailConfig.SMTP_TIMEOUT_MS);
    }

    @Test
    void an_anonymous_relay_is_not_asked_to_authenticate() {
        JavaMailSenderImpl relay = EmailConfig.relay("smtp.example.com", 587, "", "", true, false);

        assertThat(relay.getUsername()).isNull();
        assertThat(relay.getJavaMailProperties()).containsEntry("mail.smtp.auth", "false");
    }
}
