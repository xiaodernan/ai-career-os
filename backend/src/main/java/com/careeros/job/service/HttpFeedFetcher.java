package com.careeros.job.service;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import org.springframework.stereotype.Component;

/**
 * The backend's one outbound feed fetch (roadmap 19.2).
 *
 * <p>Bounded on purpose: {@link FeedUrls} refuses private addresses, the request carries
 * its own timeout, redirects are followed by hand (three hops, each re-checked, because
 * Java's own redirect policy would not consult the guard), and the body is capped at
 * 5 MB. A feed is text the server parses; anything past that is a URL someone should
 * not have subscribed to, and it fails with a sentence rather than a heap.
 */
@Component
public class HttpFeedFetcher implements FeedFetcher {

    static final int MAX_BYTES = 5 * 1024 * 1024;
    private static final int MAX_REDIRECTS = 3;
    private static final Duration CONNECT_TIMEOUT = Duration.ofSeconds(10);
    private static final Duration READ_TIMEOUT = Duration.ofSeconds(20);

    private final HttpClient client;

    public HttpFeedFetcher() {
        this(HttpClient.newBuilder()
                .connectTimeout(CONNECT_TIMEOUT)
                .followRedirects(HttpClient.Redirect.NEVER)
                .build());
    }

    HttpFeedFetcher(HttpClient client) {
        this.client = client;
    }

    @Override
    public String fetch(String url) {
        URI uri = FeedUrls.requirePublic(url);
        for (int hop = 0; hop <= MAX_REDIRECTS; hop += 1) {
            HttpResponse<InputStream> response = send(uri);
            int status = response.statusCode();
            if (status >= 300 && status < 400) {
                String location = response.headers().firstValue("Location").orElse(null);
                close(response);
                if (location == null || location.isBlank()) {
                    throw new IllegalStateException("Feed redirected without saying where");
                }
                uri = FeedUrls.requirePublic(uri.resolve(location).toString());
                continue;
            }
            if (status < 200 || status >= 300) {
                close(response);
                throw new IllegalStateException("Feed answered HTTP " + status);
            }
            try (InputStream body = response.body()) {
                return readCapped(body);
            } catch (IOException e) {
                throw new IllegalStateException("Feed body could not be read", e);
            }
        }
        throw new IllegalStateException("Feed redirected more than " + MAX_REDIRECTS + " times");
    }

    private HttpResponse<InputStream> send(URI uri) {
        HttpRequest request = HttpRequest.newBuilder(uri)
                .timeout(READ_TIMEOUT)
                .header("Accept", "application/rss+xml, application/atom+xml, "
                        + "application/json, application/xml, text/xml, */*")
                .header("User-Agent", "CareerOS/1.0 feed sweep")
                .GET()
                .build();
        try {
            return client.send(request, HttpResponse.BodyHandlers.ofInputStream());
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Feed fetch was interrupted", e);
        } catch (IOException e) {
            throw new IllegalStateException(
                    "Feed could not be reached (" + e.getClass().getSimpleName() + ")", e);
        }
    }

    private static String readCapped(InputStream body) throws IOException {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        byte[] buffer = new byte[8192];
        int total = 0;
        for (int read; (read = body.read(buffer)) != -1; ) {
            total += read;
            if (total > MAX_BYTES) {
                throw new IllegalStateException("Feed is larger than " + (MAX_BYTES / (1024 * 1024)) + " MB");
            }
            out.write(buffer, 0, read);
        }
        return out.toString(StandardCharsets.UTF_8);
    }

    private static void close(HttpResponse<InputStream> response) {
        try {
            response.body().close();
        } catch (IOException ignored) {
            // the status already decided this response's fate
        }
    }
}
