package com.careeros.mail.web;

import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import com.careeros.mail.service.MailLinks;
import com.careeros.mail.service.MailList;
import com.careeros.mail.service.MailPreferenceService;
import org.springframework.http.CacheControl;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * The same three dials, asked for by the signed-in reader rather than by an old letter
 * (roadmap 42.1).
 *
 * <p>Before this route the only way to change a mail preference was the link in a letter. A
 * reader who deleted every letter -- or who never received one -- had no way back to the
 * settings, even though the answer was sitting in their own account. The settings screen asks
 * here instead, and the address it gets is the same signed page the letters carry, so the reader
 * can also open the page a mailbox would open.
 *
 * <p>This route deliberately lives under {@code /api/v1/me} rather than {@code /api/v1/mail}: the
 * {@code /mail} prefix is {@code permitAll} for the anonymous page, so a route added under it
 * would be public until it was moved. Here the session is the credential, the three states are
 * read from the same columns the sweeps read, and the answer is {@code no-store} because the
 * signed URL it carries can change private settings.
 */
@RestController
@RequestMapping("/api/v1/me/mail")
public class MailSettingsController {

    private final MailPreferenceService preferences;
    private final MailLinks links;

    public MailSettingsController(MailPreferenceService preferences, MailLinks links) {
        this.preferences = preferences;
        this.links = links;
    }

    /** The account's dials and the page a mailbox would open; nothing here mails anyone. */
    @GetMapping("/settings")
    public ResponseEntity<MailSettings> settings(@CurrentUser AuthUser user) {
        MailSettings settings = new MailSettings(
                links.page(user.id()),
                preferences.receives(user.id(), MailList.WEEKLY),
                preferences.receives(user.id(), MailList.SIGNALS),
                preferences.receives(user.id(), MailList.REMINDERS));
        return ResponseEntity.ok()
                .cacheControl(CacheControl.noStore())
                .header("X-Robots-Tag", "noindex")
                .body(settings);
    }

    /**
     * The answer the settings card reads: the signed page's address and one boolean per dial.
     * The booleans are a summary for the card, not a second source of truth -- pressing a
     * button on the page is still what changes them.
     */
    public record MailSettings(String url, boolean weekly, boolean signals, boolean reminders) {
    }
}
