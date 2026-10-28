package com.careeros.mail.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.UUID;
import org.junit.jupiter.api.Test;

/**
 * The signed links the letters carry back (roadmap 23.1).
 *
 * <p>Five claims. The same account and secret produce the same token, so a re-sent letter
 * carries a working link. Another account's token does not validate, so one reader cannot
 * borrow another's URL. A changed character, a truncated token, an empty one and a token that
 * is not base64 at all are all simply false -- the value arrives from the open internet and
 * must not throw. The URLs share one page and differ only in the list segment, so a
 * one-click from the Monday letter can never silence the morning signals. And a blank
 * signing secret stops the boot, because an HMAC with no key signs nothing and would make
 * every account's link forgeable.
 */
class MailLinksTest {

    private static final UUID ALICE = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final UUID BOB = UUID.fromString("22222222-2222-4222-8222-222222222222");

    private final MailLinks links = new MailLinks("test-secret", "https://careeros.example");

    @Test
    void theSameAccountAndSecretProduceTheSameToken() {
        assertThat(links.token(ALICE)).isEqualTo(links.token(ALICE));
        assertThat(links.token(ALICE)).isNotEqualTo(links.token(BOB));
    }

    @Test
    void aTokenValidatesForItsOwnAccountAndNoOther() {
        assertThat(links.valid(ALICE, links.token(ALICE))).isTrue();
        assertThat(links.valid(BOB, links.token(ALICE))).isFalse();
    }

    @Test
    void aChangedTruncatedEmptyOrUnreadableTokenIsFalseRatherThanAnException() {
        String token = links.token(ALICE);
        String flipped = (token.charAt(0) == 'A' ? "B" : "A") + token.substring(1);

        assertThat(links.valid(ALICE, flipped)).isFalse();
        assertThat(links.valid(ALICE, token.substring(0, token.length() - 1))).isFalse();
        assertThat(links.valid(ALICE, "")).isFalse();
        assertThat(links.valid(ALICE, null)).isFalse();
        assertThat(links.valid(ALICE, "not base64 !!!")).isFalse();
    }

    @Test
    void aDifferentSecretRetiresEveryLinkEverMailed() {
        MailLinks rotated = new MailLinks("another-secret", "https://careeros.example");

        assertThat(rotated.valid(ALICE, links.token(ALICE))).isFalse();
    }

    @Test
    void thePageIsOneUrlAndTheOneClickDiffersOnlyByTheList() {
        String page = links.page(ALICE);

        assertThat(page).startsWith("https://careeros.example/api/v1/mail/preferences/" + ALICE + "/");
        assertThat(links.stop(ALICE, MailList.WEEKLY)).isEqualTo(page + "/stop/weekly");
        assertThat(links.stop(ALICE, MailList.SIGNALS)).isEqualTo(page + "/stop/signals");
        assertThat(links.start(ALICE, MailList.WEEKLY)).isEqualTo(page + "/start/weekly");
        assertThat(links.oneClick(ALICE, MailList.SIGNALS))
                .containsEntry(MailLinks.LIST_UNSUBSCRIBE,
                        "<" + page + "/stop/signals>")
                .containsEntry(MailLinks.LIST_UNSUBSCRIBE_POST, "List-Unsubscribe=One-Click");
    }

    @Test
    void aBaseUrlWithATrailingSlashDoesNotDoubleTheSeparator() {
        MailLinks slashed = new MailLinks("test-secret", "https://careeros.example/");

        assertThat(slashed.page(ALICE))
                .isEqualTo("https://careeros.example/api/v1/mail/preferences/" + ALICE + "/"
                        + slashed.token(ALICE));
        assertThat(slashed.webRoot()).isEqualTo("https://careeros.example");
    }

    @Test
    void aBlankSecretStopsTheBootRatherThanSigningWithNothing() {
        assertThatThrownBy(() -> new MailLinks(" ", "https://careeros.example"))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("app.mail.link-secret");
    }
}
