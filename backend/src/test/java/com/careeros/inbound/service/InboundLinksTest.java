package com.careeros.inbound.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.careeros.calendar.service.CalendarLinks;
import com.careeros.mail.service.MailLinks;
import java.nio.charset.StandardCharsets;
import java.util.UUID;
import org.junit.jupiter.api.Test;

/**
 * The inbound address is the credential (roadmap 37.1).
 *
 * <p>Six claims. The address is one account's and fits a mailbox: the local part is 45
 * octets, inside RFC 5321's 64-octet cap, so no provider rejects it. The same account signs
 * the same address twice, and another account signs another. Every way of getting the token
 * wrong -- a flipped character, a truncated one, another secret, an empty value -- names
 * nobody and never throws, because the value arrives from the open internet. The three link
 * families stay apart even though one secret signs all of them. A deployment with no domain
 * can say so and refuses to hand out an address. And a blank secret or a domain that is not a
 * bare host stops the boot, because an address that bounces is worse than an absent one.
 */
class InboundLinksTest {

    private static final UUID ALICE = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final UUID BOB = UUID.fromString("22222222-2222-4222-8222-222222222222");
    private static final String DOMAIN = "inbox.careeros.example";

    private final InboundLinks links = new InboundLinks("test-secret", DOMAIN);

    @Test
    void theAddressFitsAMailboxAndTheSameAccountSignsTheSameOne() {
        String address = links.address(ALICE);
        String local = address.substring(0, address.indexOf('@'));

        assertThat(address).isEqualTo(links.address(ALICE));
        assertThat(address).endsWith("@" + DOMAIN);
        assertThat(local.getBytes(StandardCharsets.US_ASCII)).hasSize(45);
        assertThat(local.length()).isLessThanOrEqualTo(64);
        assertThat(links.address(ALICE)).isNotEqualTo(links.address(BOB));
    }

    @Test
    void theLocalPartNamesTheAccountItSignedFor() {
        String alice = links.address(ALICE).split("@")[0];
        String bob = links.address(BOB).split("@")[0];

        assertThat(links.account(alice)).isEqualTo(ALICE);
        assertThat(links.account(bob)).isEqualTo(BOB);
    }

    @Test
    void aForgedRetiredOrUnreadableTokenNamesNobody() {
        String local = links.address(ALICE).split("@")[0];
        String forged = (local.charAt(0) == 'A' ? "B" : "A") + local.substring(1);

        assertThat(links.account(forged)).isNull();
        assertThat(links.account(local.substring(0, local.length() - 1))).isNull();
        assertThat(links.account("")).isNull();
        assertThat(links.account(null)).isNull();
        assertThat(links.account("not base64 !!!")).isNull();
        assertThat(links.account("a.b.c")).isNull();
        assertThat(new InboundLinks("another-secret", DOMAIN).account(local)).isNull();
    }

    @Test
    void aTokenWithTheRightShapeButAnUnknownSignatureNamesNobody() {
        String local = links.address(ALICE).split("@")[0];
        String account = local.substring(0, local.indexOf('.'));
        String forged = account + "."
                + java.util.Base64.getUrlEncoder().withoutPadding().encodeToString(new byte[16]);

        assertThat(links.account(forged)).isNull();
    }

    @Test
    void theThreeLinkFamiliesCannotStandInForEachOther() {
        String local = links.address(ALICE).split("@")[0];
        MailLinks mail = new MailLinks("test-secret", "https://careeros.example");
        CalendarLinks calendar = new CalendarLinks("test-secret", "https://careeros.example");

        assertThat(links.account(mail.token(ALICE))).isNull();
        assertThat(links.account(calendar.token(ALICE))).isNull();
        assertThat(mail.valid(ALICE, local)).isFalse();
        assertThat(calendar.account(local)).isNull();
    }

    @Test
    void aDeploymentWithoutADomainSaysSoInsteadOfHandingOutAnAddress() {
        InboundLinks unset = new InboundLinks("test-secret", "");

        assertThat(unset.configured()).isFalse();
        assertThatThrownBy(() -> unset.address(ALICE)).isInstanceOf(IllegalStateException.class);
        // The webhook shuts with the address: a signature over the same secret buys nothing on a
        // deployment that never handed a mailbox out.
        assertThat(unset.account(unset.localPart(ALICE))).isNull();
    }

    @Test
    void aDomainThatIsNotABareHostOrTooLongForAnAddressStopsTheBoot() {
        assertThatThrownBy(() -> new InboundLinks("test-secret", "https://inbox.example"))
                .isInstanceOf(IllegalStateException.class);
        assertThatThrownBy(() -> new InboundLinks("test-secret", "inbox@example"))
                .isInstanceOf(IllegalStateException.class);
        assertThatThrownBy(() -> new InboundLinks("test-secret", "in box.example"))
                .isInstanceOf(IllegalStateException.class);
        assertThatThrownBy(() -> new InboundLinks("test-secret", "a".repeat(254) + ".example"))
                .isInstanceOf(IllegalStateException.class);
        assertThatThrownBy(() -> new InboundLinks(" ", DOMAIN))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("app.mail.link-secret");
    }
}
