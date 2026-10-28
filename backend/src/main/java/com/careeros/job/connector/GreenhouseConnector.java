package com.careeros.job.connector;

import java.net.URI;
import java.util.Set;
import java.util.regex.Pattern;
import org.springframework.stereotype.Component;

/**
 * Greenhouse's public job board API (roadmap 19.8).
 *
 * <p>A reader configures a board by what they know: the board token ({@code acme}), the
 * public board page ({@code https://boards.greenhouse.io/acme}; newer tenants serve it
 * from {@code job-boards.greenhouse.io}), or the API URL itself. Each of the three
 * becomes the one endpoint the fetcher opens; anything else — a foreign host, a path
 * that names no board — is refused with the sentence that says what would work.
 * {@code content=true} is what makes the payload carry each posting's description, so
 * an API URL that leaves it out gets it added.
 */
@Component
public class GreenhouseConnector implements BoardConnector {

    static final String API_ROOT = "https://boards-api.greenhouse.io/v1/boards/";
    static final String SENTENCE = "A Greenhouse feed takes a board token, a "
            + "boards.greenhouse.io URL, or the board's API URL";
    private static final String API_HOST = "boards-api.greenhouse.io";
    private static final String API_PATH = "/v1/boards/";
    private static final Set<String> PAGE_HOSTS =
            Set.of("boards.greenhouse.io", "job-boards.greenhouse.io");
    private static final Pattern TOKEN = Pattern.compile("[A-Za-z0-9][A-Za-z0-9_-]{0,119}");

    @Override
    public String source() {
        return "greenhouse";
    }

    @Override
    public String apiUrl(String input) {
        String raw = input == null ? "" : input.trim();
        URI uri = BoardUrls.uriOf(raw);
        if (uri == null) {
            if (TOKEN.matcher(raw).matches()) {
                return jobsApi(raw);
            }
            throw new IllegalArgumentException(SENTENCE);
        }
        String host = BoardUrls.hostOf(uri);
        String path = uri.getPath() == null ? "" : uri.getPath();
        if (API_HOST.equals(host) && path.startsWith(API_PATH)) {
            return withContent(uri);
        }
        if (PAGE_HOSTS.contains(host)) {
            String token = BoardUrls.firstSegment(path);
            if (token != null && TOKEN.matcher(token).matches()) {
                return jobsApi(token);
            }
        }
        throw new IllegalArgumentException(SENTENCE);
    }

    private static String jobsApi(String token) {
        return API_ROOT + token + "/jobs?content=true";
    }

    /** The URL's own query, plus `content=true` when it names no content parameter yet. */
    private static String withContent(URI uri) {
        String query = uri.getRawQuery();
        if (query != null && ("content".equals(query) || query.startsWith("content=")
                || query.contains("&content="))) {
            return uri.toString();
        }
        return uri + (query == null ? "?" : "&") + "content=true";
    }
}
