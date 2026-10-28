package com.careeros.job.connector;

import java.net.URI;
import java.util.Set;
import java.util.regex.Pattern;
import org.springframework.stereotype.Component;

/**
 * Lever's public postings API (roadmap 19.8).
 *
 * <p>A reader configures a board by the company token ({@code acme}), the public board
 * page ({@code https://jobs.lever.co/acme}), or the API URL itself. The EU tenants are
 * the same shape on their own hosts, and keep their own API host — a page read from
 * {@code jobs.eu.lever.co} is fetched from {@code api.eu.lever.co}. {@code mode=json}
 * is appended to an API URL that names no mode, because the endpoint's other mode is a
 * page, not a payload.
 */
@Component
public class LeverConnector implements BoardConnector {

    static final String API_ROOT = "https://api.lever.co/v0/postings/";
    static final String EU_API_ROOT = "https://api.eu.lever.co/v0/postings/";
    static final String SENTENCE = "A Lever feed takes a company token, a jobs.lever.co URL, "
            + "or the board's API URL";
    private static final String API_PATH = "/v0/postings/";
    private static final Set<String> API_HOSTS = Set.of("api.lever.co", "api.eu.lever.co");
    private static final Set<String> PAGE_HOSTS = Set.of("jobs.lever.co", "jobs.eu.lever.co");
    private static final Pattern TOKEN = Pattern.compile("[A-Za-z0-9][A-Za-z0-9-]{0,119}");

    @Override
    public String source() {
        return "lever";
    }

    @Override
    public String apiUrl(String input) {
        String raw = input == null ? "" : input.trim();
        URI uri = BoardUrls.uriOf(raw);
        if (uri == null) {
            if (TOKEN.matcher(raw).matches()) {
                return postings(raw, API_ROOT);
            }
            throw new IllegalArgumentException(SENTENCE);
        }
        String host = BoardUrls.hostOf(uri);
        String path = uri.getPath() == null ? "" : uri.getPath();
        if (API_HOSTS.contains(host) && path.startsWith(API_PATH)) {
            String token = BoardUrls.firstSegment(path.substring(API_PATH.length()));
            if (token != null && TOKEN.matcher(token).matches()) {
                return withMode(uri);
            }
        }
        if (PAGE_HOSTS.contains(host)) {
            String token = BoardUrls.firstSegment(path);
            if (token != null && TOKEN.matcher(token).matches()) {
                return postings(token, host.startsWith("jobs.eu.") ? EU_API_ROOT : API_ROOT);
            }
        }
        throw new IllegalArgumentException(SENTENCE);
    }

    private static String postings(String token, String root) {
        return root + token + "?mode=json";
    }

    /** The URL's own query, plus `mode=json` when it names no mode yet. */
    private static String withMode(URI uri) {
        String query = uri.getRawQuery();
        if (query != null && ("mode".equals(query) || query.startsWith("mode=")
                || query.contains("&mode="))) {
            return uri.toString();
        }
        return uri + (query == null ? "?" : "&") + "mode=json";
    }
}
