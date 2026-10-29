package com.careeros.common;

import jakarta.servlet.http.HttpServletRequest;

/**
 * Who opened a session: the user-agent and the address that presented the credentials.
 * Recorded once per refresh-token family so the account can later recognise its own
 * sessions. Both fields are best-effort — a client may omit the agent, and the address
 * is only as trustworthy as the proxy in front of us — and both are truncated to the
 * column widths (255 / 45) so an oversized header cannot fail the insert.
 */
public record ClientInfo(String userAgent, String clientIp) {

    public static final ClientInfo NONE = new ClientInfo(null, null);

    private static final int USER_AGENT_MAX = 255;
    private static final int ADDRESS_MAX = 45;

    public static ClientInfo from(HttpServletRequest request, boolean trustForwardedFor) {
        return new ClientInfo(truncate(request.getHeader("User-Agent"), USER_AGENT_MAX),
                truncate(clientIp(request, trustForwardedFor), ADDRESS_MAX));
    }

    /**
     * The address the caller is counted against.
     *
     * <p>X-Forwarded-For is hearsay: a client can write any value into it. It is only
     * read when the deployment declares a trusted reverse proxy in front of this
     * service ({@code app.http.trust-forwarded-for}); without that declaration the
     * socket's address is the answer, so rotating the header buys nothing.
     *
     * <p>When trusted, the <em>last</em> hop is read rather than the first. The proxy
     * may overwrite the header with the address it saw, or append to what the client
     * sent; in both shapes the hop the proxy itself wrote is the rightmost one, and
     * anything to its left is text the client chose. Reading the leftmost entry was
     * the spoofable read even behind an appending proxy.
     */
    public static String clientIp(HttpServletRequest request, boolean trustForwardedFor) {
        if (!trustForwardedFor) {
            return request.getRemoteAddr();
        }
        String forwarded = request.getHeader("X-Forwarded-For");
        if (forwarded == null || forwarded.isBlank()) {
            return request.getRemoteAddr();
        }
        String[] hops = forwarded.split(",");
        for (int i = hops.length - 1; i >= 0; i--) {
            String hop = hops[i].trim();
            if (!hop.isEmpty()) {
                return hop;
            }
        }
        return request.getRemoteAddr();
    }

    private static String truncate(String value, int max) {
        if (value == null || value.isBlank()) {
            return null;
        }
        String trimmed = value.trim();
        return trimmed.length() <= max ? trimmed : trimmed.substring(0, max);
    }
}
