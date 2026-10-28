package com.careeros.job.service;

import java.net.Inet4Address;
import java.net.InetAddress;
import java.net.URI;
import java.net.UnknownHostException;

/**
 * What a feed URL is allowed to point at (roadmap 19.2).
 *
 * <p>The server fetches a URL the user typed, so the URL is a request to make the server
 * open a connection -- and the interesting addresses are the ones that are not on the
 * public internet: `127.0.0.1`, `10.0.0.5`, the cloud metadata endpoint at
 * `169.254.169.254`. Those are refused here, at the last moment before a socket is
 * opened, by resolving the name and checking every address it answers with. A DNS
 * answer can change between this check and the connect (rebinding); this is defence in
 * depth, not a proof, and it is written down as such rather than implied.
 *
 * <p>Registration only checks the shape (scheme + host), because saving a feed should
 * not depend on the network the server is having today. The address check runs on every
 * fetch, and on every redirect target as well -- a public URL that answers `302
 * http://169.254.169.254/` is the same request one hop later.
 */
final class FeedUrls {

    private FeedUrls() {
    }

    /** The shape check registration uses: an absolute http(s) URL with a host. */
    static boolean isHttpUrl(String raw) {
        if (raw == null || raw.isBlank() || raw.length() > 2048) {
            return false;
        }
        try {
            URI uri = URI.create(raw.trim());
            return isHttp(uri) && host(uri) != null;
        } catch (IllegalArgumentException e) {
            return false;
        }
    }

    /**
     * The URL a fetch may actually open: right shape, host resolves, and none of its
     * addresses is loopback, private, link-local, carrier-grade NAT or multicast.
     */
    static URI requirePublic(String raw) {
        if (!isHttpUrl(raw)) {
            throw new IllegalStateException("Feed URL must be an http(s) address");
        }
        URI uri = URI.create(raw.trim());
        String host = host(uri);
        InetAddress[] addresses;
        try {
            addresses = InetAddress.getAllByName(host);
        } catch (UnknownHostException e) {
            throw new IllegalStateException("Feed host cannot be resolved: " + host);
        }
        for (InetAddress address : addresses) {
            if (!isPublic(address)) {
                throw new IllegalStateException(
                        "Feed URL points at a private or local address, which the server will not fetch");
            }
        }
        return uri;
    }

    private static boolean isHttp(URI uri) {
        String scheme = uri.getScheme();
        return "http".equalsIgnoreCase(scheme) || "https".equalsIgnoreCase(scheme);
    }

    /** `getHost()` keeps an IPv6 literal's brackets; `InetAddress` wants it bare. */
    private static String host(URI uri) {
        String host = uri.getHost();
        if (host == null) {
            return null;
        }
        if (host.startsWith("[") && host.endsWith("]")) {
            return host.substring(1, host.length() - 1);
        }
        return host;
    }

    private static boolean isPublic(InetAddress address) {
        if (address.isAnyLocalAddress() || address.isLoopbackAddress()
                || address.isLinkLocalAddress() || address.isSiteLocalAddress()
                || address.isMulticastAddress()) {
            return false;
        }
        byte[] bytes = address.getAddress();
        if (bytes.length == 16 && (bytes[0] & 0xfe) == 0xfc) {
            return false; // unique-local fc00::/7, which isSiteLocalAddress does not cover
        }
        if (address instanceof Inet4Address && bytes.length == 4
                && (bytes[0] & 0xff) == 100 && (bytes[1] & 0xc0) == 64) {
            return false; // 100.64.0.0/10, carrier-grade NAT
        }
        return true;
    }
}
