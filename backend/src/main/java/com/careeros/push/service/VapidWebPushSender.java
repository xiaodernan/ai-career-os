package com.careeros.push.service;

import com.careeros.push.entity.PushSubscription;
import io.jsonwebtoken.Jwts;
import java.net.URI;
import java.net.http.HttpClient;
import java.time.Duration;
import java.time.Instant;
import java.util.Date;
import java.util.Locale;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpHeaders;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;

/**
 * The VAPID transport of {@link PushSender} (roadmap 33.2, RFC 8030/8292).
 *
 * <p>One wake is one {@code POST} with no body. The Authorization header carries an ES256 JWT
 * scoped to the <em>origin</em> of the endpoint -- a push service checks the {@code aud} claim
 * against the origin it was reached on, so a token minted for one service is not replayable
 * against another -- and the deployment's public key as {@code k}. The {@code TTL} header is
 * how long the push service may hold the wake for a browser that is offline; the shipped
 * default is half a day, because a morning signal pushed two days later is not news.
 *
 * <p>There is deliberately no payload and no encryption: the worker asks the authenticated
 * inbox what is new. A push service therefore learns only that <em>some</em> account's browser
 * exists at this endpoint (which it issued itself) and that it was asked to wake; not a signal,
 * a saved-search name or a count -- the same reason the endpoint is never printed in a log
 * line, only the service's host.
 *
 * <p>A {@code 404} or {@code 410} is the push service saying the registration no longer exists;
 * the caller deletes the row. Every other refusal is returned as such and not retried here: one
 * pass is one attempt per registration, and the sweep decides what the morning does next. The
 * transport never throws -- a sweep walking many browsers must not stop at the first one that
 * timed out.
 */
public class VapidWebPushSender implements PushSender {

    private static final Logger log = LoggerFactory.getLogger(VapidWebPushSender.class);

    /** RFC 8292 caps the token's lifetime at 24 hours; twelve is long enough for one morning. */
    static final long JWT_TTL_SECONDS = 12 * 60 * 60;

    /** RFC 8030's own ceiling for TTL, four weeks; anything above is a client error. */
    public static final int MAX_TTL_SECONDS = 4 * 7 * 24 * 60 * 60;

    private static final Duration CONNECT_TIMEOUT = Duration.ofSeconds(5);
    private static final Duration READ_TIMEOUT = Duration.ofSeconds(10);

    private final VapidKeys keys;
    private final String subject;
    private final int ttlSeconds;
    private final RestClient rest;

    public VapidWebPushSender(VapidKeys keys, String subject, int ttlSeconds) {
        this(defaultClient(), keys, subject, ttlSeconds);
    }

    VapidWebPushSender(RestClient rest, VapidKeys keys, String subject, int ttlSeconds) {
        if (ttlSeconds <= 0 || ttlSeconds > MAX_TTL_SECONDS) {
            throw new IllegalStateException("app.push.ttl-seconds must be between 1 and "
                    + MAX_TTL_SECONDS + " (RFC 8030's ceiling)");
        }
        if (subject == null || subject.isBlank()) {
            throw new IllegalStateException("a VAPID sender needs a subject: app.push.contact "
                    + "or the deployment's app.web.base-url");
        }
        this.keys = keys;
        this.subject = subject;
        this.ttlSeconds = ttlSeconds;
        this.rest = rest;
    }

    /**
     * A push service that stops answering must not hold the morning sweep open; JDK
     * HttpClient defaults to HTTP/2, which every push service also speaks, so the upgrade
     * probe the ai-service client had to turn off is not needed here.
     */
    static RestClient defaultClient() {
        HttpClient httpClient = HttpClient.newBuilder()
                .connectTimeout(CONNECT_TIMEOUT)
                .build();
        JdkClientHttpRequestFactory factory = new JdkClientHttpRequestFactory(httpClient);
        factory.setReadTimeout(READ_TIMEOUT);
        return RestClient.builder().requestFactory(factory).build();
    }

    @Override
    public Outcome send(PushSubscription subscription) {
        URI endpoint;
        try {
            endpoint = URI.create(subscription.getEndpointUrl());
        } catch (IllegalArgumentException e) {
            log.warn("push subscription {} has no usable endpoint", subscription.getId());
            return Outcome.REFUSED;
        }
        String origin = origin(endpoint);
        if (origin == null) {
            log.warn("push subscription {} has no https origin to address", subscription.getId());
            return Outcome.REFUSED;
        }
        try {
            int status = rest.post()
                    .uri(endpoint)
                    .header(HttpHeaders.AUTHORIZATION, authorization(origin))
                    .header("TTL", Integer.toString(ttlSeconds))
                    .exchange((request, response) -> response.getStatusCode().value());
            if (status >= 200 && status < 300) {
                return Outcome.SENT;
            }
            if (status == 404 || status == 410) {
                log.info("push service retired the registration {}", subscription.getId());
                return Outcome.GONE;
            }
            log.warn("push service {} refused a wake with status {}", endpoint.getHost(), status);
            return Outcome.REFUSED;
        } catch (ResourceAccessException e) {
            log.warn("push service {} could not be reached: {}", endpoint.getHost(), e.getMessage());
            return Outcome.REFUSED;
        } catch (RuntimeException e) {
            log.warn("push service {} answered a wake that could not be read", endpoint.getHost(), e);
            return Outcome.REFUSED;
        }
    }

    /** `vapid t=<jwt>, k=<public key>`: the scheme name, a space, then two comma-separated values. */
    String authorization(String origin) {
        return "vapid t=" + token(origin) + ", k=" + keys.publicKeyBase64Url();
    }

    /** The ES256 JWT: `typ` and `alg` in the header, the origin and the deployment's contact inside. */
    String token(String origin) {
        Instant now = Instant.now();
        return Jwts.builder()
                .header().type("JWT").and()
                .audience().add(origin).and()
                .subject(subject)
                .issuedAt(Date.from(now))
                .expiration(Date.from(now.plusSeconds(JWT_TTL_SECONDS)))
                .signWith(keys.privateKey(), Jwts.SIG.ES256)
                .compact();
    }

    /**
     * The origin a push service checks `aud` against: scheme, host and port, lowercased, with
     * no path -- the endpoint's path is the registration, the origin is the service.
     */
    static String origin(URI endpoint) {
        String scheme = endpoint.getScheme();
        String host = endpoint.getHost();
        if (scheme == null || host == null || !"https".equalsIgnoreCase(scheme)) {
            return null;
        }
        return scheme.toLowerCase(Locale.ROOT) + "://"
                + host.toLowerCase(Locale.ROOT)
                + (endpoint.getPort() == -1 ? "" : ":" + endpoint.getPort());
    }
}
