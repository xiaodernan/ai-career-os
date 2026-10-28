package com.careeros.job.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

/**
 * What a feed URL may point at (roadmap 19.2).
 *
 * <p>The server opens a connection to a URL the user typed, so the guard is the whole
 * difference between "fetch my feed" and "read the host's own network". The interesting
 * addresses are the ones that are not on the public internet, and each family has its
 * own way of spelling itself: loopback, RFC 1918 private space, link-local (where the
 * cloud metadata endpoint lives), carrier-grade NAT, and IPv6's unique-local range.
 * They are all refused, by address rather than by hostname, because a name can answer
 * with any of them.
 *
 * <p>Registration checks only the shape — an absolute http(s) URL with a host — because
 * saving a subscription should not depend on today's DNS; the address check runs on
 * every fetch and on every redirect target. Numeric addresses are used here so the test
 * resolves nothing over the network.
 */
class FeedUrlsTest {

    @Test
    void theShapeCheckAcceptsAnAbsoluteHttpAddress() {
        assertThat(FeedUrls.isHttpUrl("https://boards.example.com/rss.xml")).isTrue();
        assertThat(FeedUrls.isHttpUrl("http://boards.example.com/api/jobs?page=2")).isTrue();
        assertThat(FeedUrls.isHttpUrl("  https://boards.example.com/rss.xml  ")).isTrue();
    }

    @Test
    void theShapeCheckRefusesAnythingElse() {
        assertThat(FeedUrls.isHttpUrl(null)).isFalse();
        assertThat(FeedUrls.isHttpUrl("   ")).isFalse();
        assertThat(FeedUrls.isHttpUrl("boards.example.com/rss")).isFalse();
        assertThat(FeedUrls.isHttpUrl("ftp://boards.example.com/rss")).isFalse();
        assertThat(FeedUrls.isHttpUrl("javascript:alert(1)")).isFalse();
        assertThat(FeedUrls.isHttpUrl("file:///etc/passwd")).isFalse();
        assertThat(FeedUrls.isHttpUrl("http://")).isFalse();
        assertThat(FeedUrls.isHttpUrl("https://" + "a".repeat(2048) + "/rss")).isFalse();
    }

    @Test
    void aLoopbackAddressIsRefusedWhenTheFetchWouldOpenIt() {
        assertRefused("http://127.0.0.1/feed");
        assertRefused("http://[::1]/feed");
    }

    @Test
    void privateLinkLocalAndCarrierGradeAddressesAreRefused() {
        assertRefused("http://10.0.0.5/feed");
        assertRefused("http://192.168.1.10/feed");
        assertRefused("http://172.16.4.2/feed");
        assertRefused("http://169.254.169.254/latest/meta-data");
        assertRefused("http://100.64.0.1/feed");
        assertRefused("http://224.0.0.1/feed");
    }

    @Test
    void anIpv6UniqueLocalAddressIsRefused() {
        assertRefused("http://[fc00::1]/feed");
        assertRefused("http://[fd12:3456:789a::1]/feed");
    }

    @Test
    void aPublicLiteralIsAllowedAndAnsweredWithItsUri() {
        assertThat(FeedUrls.requirePublic("http://8.8.8.8/feed").getHost()).isEqualTo("8.8.8.8");
    }

    @Test
    void aBadShapeIsRefusedBeforeAnyResolutionHappens() {
        assertThatThrownBy(() -> FeedUrls.requirePublic("boards.example.com/rss"))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("http");
    }

    private static void assertRefused(String url) {
        assertThatThrownBy(() -> FeedUrls.requirePublic(url))
                .as("feed URL %s", url)
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("private or local address");
    }
}
