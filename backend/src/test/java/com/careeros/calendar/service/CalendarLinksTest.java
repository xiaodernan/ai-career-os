package com.careeros.calendar.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.careeros.mail.service.MailLinks;
import java.util.UUID;
import org.junit.jupiter.api.Test;

/**
 * The calendar feed's address is the credential (roadmap 34.1).
 *
 * <p>Five claims, four of them the mail links' own repeated because a second credential must
 * not be weaker than the first: the same account signs to the same token, so a calendar app
 * polling twice is polling one feed; another account's token names nobody; a changed,
 * truncated, empty or unreadable token is null rather than an exception, because the value
 * arrives from the open internet; a rotated secret retires every URL ever handed out.
 *
 * <p>The fifth is the domain separation. The two link families share
 * {@code app.mail.link-secret}, so the prefixes are what keeps them apart: a mail token must
 * not open a calendar, and a calendar token must not stand in for a mail link. Without it one
 * leaked unsubscribe URL would be a calendar subscription and vice versa -- the same key
 * signing two meanings.
 */
class CalendarLinksTest {

    private static final UUID ALICE = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final UUID BOB = UUID.fromString("22222222-2222-4222-8222-222222222222");

    private final CalendarLinks links = new CalendarLinks("test-secret", "https://careeros.example");

    @Test
    void theSameAccountSignsTheSameAddressAndAnotherSignsAnother() {
        assertThat(links.token(ALICE)).isEqualTo(links.token(ALICE));
        assertThat(links.token(ALICE)).isNotEqualTo(links.token(BOB));
        assertThat(links.account(links.token(ALICE))).isEqualTo(ALICE);
        assertThat(links.account(links.token(BOB))).isEqualTo(BOB);
    }

    @Test
    void aForgedRetiredOrUnreadableTokenNamesNobody() {
        String token = links.token(ALICE);
        String flipped = (token.charAt(0) == 'A' ? "B" : "A") + token.substring(1);

        assertThat(links.account(flipped)).isNull();
        assertThat(links.account(token.substring(0, token.length() - 1))).isNull();
        assertThat(links.account("")).isNull();
        assertThat(links.account(null)).isNull();
        assertThat(links.account("not base64 !!!")).isNull();
        assertThat(new CalendarLinks("another-secret", "https://careeros.example").account(token)).isNull();
    }

    @Test
    void aTokenWithTheRightShapeButAnUnknownSignatureNamesNobody() {
        // The account id is real and the signature is thirty-two zero bytes: every field parses,
        // and only the MAC decides.
        String forged = ALICE + "."
                + java.util.Base64.getUrlEncoder().withoutPadding().encodeToString(new byte[32]);
        assertThat(links.account(forged)).isNull();
    }

    @Test
    void aMailLinkTokenIsNotACalendarTokenAndTheReverseHoldsToo() {
        MailLinks mail = new MailLinks("test-secret", "https://careeros.example");

        assertThat(mail.valid(ALICE, mail.token(ALICE))).isTrue();
        assertThat(links.account(mail.token(ALICE))).isNull();
        assertThat(mail.valid(ALICE, links.token(ALICE))).isFalse();
    }

    @Test
    void theAddressIsTheFeedRouteWithTheTokenAndAnAbsoluteOrigin() {
        assertThat(links.feed(ALICE))
                .isEqualTo("https://careeros.example/api/v1/calendar.ics?token=" + links.token(ALICE));
        assertThat(links.webRoot()).isEqualTo("https://careeros.example");
    }

    @Test
    void aTrailingSlashDoesNotDoubleTheSeparator() {
        CalendarLinks slashed = new CalendarLinks("test-secret", "https://careeros.example/");

        assertThat(slashed.feed(ALICE))
                .isEqualTo("https://careeros.example/api/v1/calendar.ics?token=" + slashed.token(ALICE));
        assertThat(slashed.webRoot()).isEqualTo("https://careeros.example");
    }

    @Test
    void aBlankSecretStopsTheBootRatherThanSigningWithNothing() {
        assertThatThrownBy(() -> new CalendarLinks(" ", "https://careeros.example"))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("app.mail.link-secret");
    }
}
