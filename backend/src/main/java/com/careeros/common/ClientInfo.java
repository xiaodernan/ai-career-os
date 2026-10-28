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

    public static ClientInfo from(HttpServletRequest request) {
        return new ClientInfo(truncate(request.getHeader("User-Agent"), USER_AGENT_MAX),
                truncate(clientIp(request), ADDRESS_MAX));
    }

    /**
     * Deployments sit behind a trusted reverse proxy that sets X-Forwarded-For; direct
     * clients cannot spoof it there. Shared with the rate limiter so the two readers of
     * "who is calling" can never disagree.
     */
    public static String clientIp(HttpServletRequest request) {
        String forwarded = request.getHeader("X-Forwarded-For");
        if (forwarded != null && !forwarded.isBlank()) {
            return forwarded.split(",")[0].trim();
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
