package com.careeros.mail.web;

import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import com.careeros.mail.service.MailLinks;
import com.careeros.mail.service.MailList;
import com.careeros.mail.service.MailPreferenceService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import org.springframework.http.CacheControl;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * The same three dials, asked for and settled by the signed-in reader rather than by an old
 * letter (roadmap 42.1, 42.2).
 *
 * <p>Before this route the only way to change a mail preference was the link in a letter. A
 * reader who deleted every letter -- or who never received one -- had no way back to the
 * settings, even though the answer was sitting in their own account. The settings screen reads
 * here and writes here now, and the address it gets is the same signed page the letters carry,
 * so the reader can also open the page a mailbox would open.
 *
 * <p>This route deliberately lives under {@code /api/v1/me} rather than {@code /api/v1/mail}: the
 * {@code /mail} prefix is {@code permitAll} for the anonymous page, so a route added under it
 * would be public until it was moved. Here the session is the credential, the three states come
 * from the same columns the sweeps read, and the answer is {@code no-store} because the signed
 * URL it carries can change private settings.
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
     * One dial, settled from the settings screen (42.2). The write goes through the same service
     * the signed page's buttons call, so the two surfaces cannot disagree about what "off" means
     * -- and the answer is the whole page again, because turning one dial off must not make the
     * card guess what the other two are.
     *
     * <p>A slug none of the lists spells is a 400 of its own. Only the browser builds it, so a
     * reader meets this when a build and the service disagree -- a sentence about a mail setting,
     * not about an address.
     */
    @PutMapping("/settings/{list}")
    public ResponseEntity<MailSettings> set(@CurrentUser AuthUser user,
                                            @PathVariable String list,
                                            @RequestBody @Valid MailDialRequest dial) {
        MailList which = MailList.of(list);
        if (which == null) {
            throw new ApiException(ApiErrorCode.MAIL_LIST_UNKNOWN, "Unknown mail list: " + list);
        }
        preferences.set(user.id(), which, dial.enabled());
        return settings(user);
    }

    /**
     * The answer the settings card reads: the signed page's address and one boolean per dial.
     * The booleans come from the same columns the sweeps read -- the card's switches and the
     * page's buttons are two doors to one state, not two answers.
     */
    public record MailSettings(String url, boolean weekly, boolean signals, boolean reminders) {
    }

    /**
     * The one field a dial write binds. {@code Boolean} rather than {@code boolean} on purpose: an
     * absent field has to be a refusal, not an accidental "off". A body without {@code enabled}
     * is a malformed write -- turning the Monday letter off because a client forgot the field is
     * exactly the silent change this route must not make.
     */
    public record MailDialRequest(@NotNull Boolean enabled) {
    }
}
