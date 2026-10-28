package com.careeros.job.connector;

import java.net.URI;
import java.util.Locale;

/** The URI reading both board connectors do, in one place. */
final class BoardUrls {

    private BoardUrls() {
    }

    /** The URL when it is an absolute http(s) address with a host, else null. */
    static URI uriOf(String raw) {
        if (raw == null || !raw.contains("://")) {
            return null;
        }
        try {
            URI uri = URI.create(raw);
            String scheme = uri.getScheme();
            boolean http = "http".equalsIgnoreCase(scheme) || "https".equalsIgnoreCase(scheme);
            return http && uri.getHost() != null ? uri : null;
        } catch (IllegalArgumentException e) {
            return null;
        }
    }

    static String hostOf(URI uri) {
        String host = uri.getHost();
        return host == null ? "" : host.toLowerCase(Locale.ROOT);
    }

    /** The first non-blank path segment, which is the board token on both boards' pages. */
    static String firstSegment(String path) {
        for (String segment : path.split("/")) {
            if (!segment.isBlank()) {
                return segment;
            }
        }
        return null;
    }
}
