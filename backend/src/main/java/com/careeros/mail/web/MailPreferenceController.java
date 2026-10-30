package com.careeros.mail.web;

import com.careeros.auth.entity.User;
import com.careeros.auth.repository.UserRepository;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.mail.service.MailLinks;
import com.careeros.mail.service.MailList;
import com.careeros.mail.service.MailPreferenceService;
import java.nio.charset.StandardCharsets;
import java.util.UUID;
import org.springframework.http.CacheControl;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * The way out of the mail (roadmap 23.1, 41.1), reachable from a mailbox and from nowhere else.
 *
 * <p>No login: a mail client cannot carry the app's bearer token, and asking a reader to sign in
 * to stop mail is how a complaint becomes spam. The account id and its HMAC travel in the path,
 * so the link is the credential; every response is {@code no-store} because the page states
 * private settings.
 *
 * <p>Reading and changing are different verbs on purpose. Mail clients and security scanners
 * prefetch links in letters, so a {@code GET} must never flip a dial: it renders every state
 * with the buttons that do. The change travels only through {@code POST} -- the button's form
 * for a reader, the RFC 8058 one-click URL in the letter's headers for a client that offered
 * "unsubscribe" beside the sender. Both are the same handler, and both are idempotent, so a
 * double-click or a repeated one-click settles the same state.
 *
 * <p>An unreadable id, a signature that is not this account's, an unknown list or a deleted
 * account are all one answer: 404 with the same sentence. The URL arrives from the open
 * internet, and telling a forger which half was wrong would grade their guesses.
 */
@RestController
@RequestMapping("/api/v1/mail")
public class MailPreferenceController {

    private static final MediaType HTML = MediaType.parseMediaType("text/html;charset=UTF-8");
    private static final String NO_LINK = "This mail-settings link is not valid or has been retired";

    private final MailPreferenceService preferences;
    private final MailLinks links;
    private final UserRepository users;

    public MailPreferenceController(MailPreferenceService preferences, MailLinks links,
                                    UserRepository users) {
        this.preferences = preferences;
        this.links = links;
        this.users = users;
    }

    /** The page the letter's footer opens: both dials, no change. */
    @GetMapping("/preferences/{userId}/{token}")
    public ResponseEntity<byte[]> page(@PathVariable String userId, @PathVariable String token) {
        User account = account(userId, token);
        return render(account, false);
    }

    /** The one-click unsubscribe a mail client fires; the body is deliberately not read. */
    @PostMapping("/preferences/{userId}/{token}/stop/{list}")
    public ResponseEntity<byte[]> stop(@PathVariable String userId, @PathVariable String token,
                                       @PathVariable String list) {
        return change(userId, token, list, false);
    }

    /** The page's "turn it back on" button. */
    @PostMapping("/preferences/{userId}/{token}/start/{list}")
    public ResponseEntity<byte[]> start(@PathVariable String userId, @PathVariable String token,
                                        @PathVariable String list) {
        return change(userId, token, list, true);
    }

    private ResponseEntity<byte[]> change(String userId, String token, String list,
                                          boolean enabled) {
        User account = account(userId, token);
        MailList which = MailList.of(list);
        if (which == null) {
            throw new ApiException(ApiErrorCode.MAIL_LINK_INVALID, NO_LINK);
        }
        preferences.set(account.getId(), which, enabled);
        return render(account, true);
    }

    private ResponseEntity<byte[]> render(User account, boolean changed) {
        String html = MailPage.render(
                account.getLocale(),
                preferences.receives(account.getId(), MailList.WEEKLY),
                preferences.receives(account.getId(), MailList.SIGNALS),
                preferences.receives(account.getId(), MailList.REMINDERS),
                links.page(account.getId()),
                changed);
        return ResponseEntity.ok()
                .contentType(HTML)
                .cacheControl(CacheControl.noStore())
                .header("X-Robots-Tag", "noindex")
                .body(html.getBytes(StandardCharsets.UTF_8));
    }

    /** The account this URL names, or the one 404 every bad URL gets. */
    private User account(String rawId, String token) {
        UUID id = canonical(rawId);
        if (id == null || !links.valid(id, token)) {
            throw new ApiException(ApiErrorCode.MAIL_LINK_INVALID, NO_LINK);
        }
        return users.findById(id)
                .orElseThrow(() -> new ApiException(ApiErrorCode.MAIL_LINK_INVALID, NO_LINK));
    }

    private static UUID canonical(String rawId) {
        try {
            return UUID.fromString(rawId);
        } catch (IllegalArgumentException e) {
            return null;
        }
    }
}
