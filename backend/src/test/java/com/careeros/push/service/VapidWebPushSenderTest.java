package com.careeros.push.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.content;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withStatus;

import com.careeros.push.entity.PushSubscription;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jws;
import io.jsonwebtoken.Jwts;
import java.net.URI;
import java.security.KeyPair;
import java.security.interfaces.ECPrivateKey;
import java.security.interfaces.ECPublicKey;
import java.time.Instant;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

/**
 * The wire a VAPID wake actually is (roadmap 33.2), read off a mock push service: the method,
 * the two headers, the empty body, the token's claims and signature, and what each answer means.
 */
class VapidWebPushSenderTest {

    private static final String ENDPOINT = "https://push.example.com/f/privacy-7a1f";
    private static final String ORIGIN = "https://push.example.com";
    private static final String SUBJECT = "mailto:ops@career.example.org";

    private final KeyPair pair = VapidTestKeys.generate();
    private final ECPublicKey publicKey = (ECPublicKey) pair.getPublic();
    private final ECPrivateKey privateKey = (ECPrivateKey) pair.getPrivate();
    private final VapidKeys keys = VapidKeys.parse(VapidTestKeys.publicKey(publicKey),
            VapidTestKeys.rawPrivateKey(privateKey));

    @Test
    void aWakeIsAnEmptySignedPostForTheEndpointsOrigin() {
        RestClient.Builder builder = RestClient.builder();
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        VapidWebPushSender sender = new VapidWebPushSender(builder.build(), keys, SUBJECT, 43200);
        String[] authorization = new String[1];
        server.expect(requestTo(ENDPOINT))
                .andExpect(method(HttpMethod.POST))
                .andExpect(header("TTL", "43200"))
                .andExpect(content().bytes(new byte[0]))
                .andExpect(request -> authorization[0] =
                        request.getHeaders().getFirst(HttpHeaders.AUTHORIZATION))
                .andRespond(withStatus(HttpStatus.CREATED));

        assertThat(sender.send(subscription(ENDPOINT))).isEqualTo(PushSender.Outcome.SENT);
        server.verify();

        assertThat(authorization[0]).startsWith("vapid t=").contains(", k=" + keys.publicKeyBase64Url());
        String token = authorization[0].substring("vapid t=".length(),
                authorization[0].indexOf(", k="));
        Jws<Claims> parsed = Jwts.parser().verifyWith(publicKey).build().parseSignedClaims(token);
        assertThat(parsed.getHeader().getAlgorithm()).isEqualTo("ES256");
        assertThat(parsed.getHeader().getType()).isEqualTo("JWT");
        Claims claims = parsed.getPayload();
        assertThat(claims.getAudience()).containsExactly(ORIGIN);
        assertThat(claims.getSubject()).isEqualTo(SUBJECT);
        long lifetime = claims.getExpiration().toInstant().getEpochSecond()
                - Instant.now().getEpochSecond();
        assertThat(lifetime).isBetween(11 * 3600L, 12 * 3600L);
    }

    @Test
    void aNoneDefaultPortIsPartOfTheAudience() {
        String endpoint = "https://push.example.com:8443/f/privacy";
        RestClient.Builder builder = RestClient.builder();
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        VapidWebPushSender sender = new VapidWebPushSender(builder.build(), keys, SUBJECT, 60);
        server.expect(requestTo(endpoint)).andRespond(withStatus(HttpStatus.CREATED));

        assertThat(sender.send(subscription(endpoint))).isEqualTo(PushSender.Outcome.SENT);
        server.verify();
        // The origin with the port is what a push service checks `aud` against.
        String token = sender.token("https://push.example.com:8443");
        Claims claims = Jwts.parser().verifyWith(publicKey).build().parseSignedClaims(token).getPayload();
        assertThat(claims.getAudience()).containsExactly("https://push.example.com:8443");
    }

    @Test
    void aRetiredRegistrationIsGone() {
        for (HttpStatus retired : new HttpStatus[] {HttpStatus.NOT_FOUND, HttpStatus.GONE}) {
            RestClient.Builder builder = RestClient.builder();
            MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
            VapidWebPushSender sender = new VapidWebPushSender(builder.build(), keys, SUBJECT, 43200);
            server.expect(requestTo(ENDPOINT)).andRespond(withStatus(retired));

            assertThat(sender.send(subscription(ENDPOINT)))
                    .as("status %s", retired.value())
                    .isEqualTo(PushSender.Outcome.GONE);
            server.verify();
        }
    }

    @Test
    void everyOtherAnswerIsARefusalAndNotRetried() {
        for (HttpStatus refused : new HttpStatus[] {HttpStatus.BAD_REQUEST, HttpStatus.UNAUTHORIZED,
                HttpStatus.FORBIDDEN, HttpStatus.TOO_MANY_REQUESTS, HttpStatus.SERVICE_UNAVAILABLE}) {
            RestClient.Builder builder = RestClient.builder();
            MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
            VapidWebPushSender sender = new VapidWebPushSender(builder.build(), keys, SUBJECT, 43200);
            server.expect(requestTo(ENDPOINT)).andRespond(withStatus(refused));

            assertThat(sender.send(subscription(ENDPOINT)))
                    .as("status %s", refused.value())
                    .isEqualTo(PushSender.Outcome.REFUSED);
            server.verify();
        }
    }

    @Test
    void anEndpointThatIsNotHttpsIsRefusedWithoutAWake() {
        RestClient.Builder builder = RestClient.builder();
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        VapidWebPushSender sender = new VapidWebPushSender(builder.build(), keys, SUBJECT, 43200);

        assertThat(sender.send(subscription("http://push.example.com/f/privacy")))
                .isEqualTo(PushSender.Outcome.REFUSED);
        assertThat(sender.send(subscription("not a url"))).isEqualTo(PushSender.Outcome.REFUSED);
        server.verify();
    }

    @Test
    void aTtlOutsideTheRfcCeilingOrASubjectlessSenderIsABootRefusal() {
        assertThatThrownBy(() -> new VapidWebPushSender(keys, SUBJECT, 0))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("app.push.ttl-seconds");
        assertThatThrownBy(() -> new VapidWebPushSender(keys, SUBJECT,
                VapidWebPushSender.MAX_TTL_SECONDS + 1))
                .isInstanceOf(IllegalStateException.class);
        assertThatThrownBy(() -> new VapidWebPushSender(keys, " ", 43200))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("subject");
    }

    @Test
    void theOriginIsTheServiceNotTheRegistrationPath() {
        assertThat(VapidWebPushSender.origin(URI.create(ENDPOINT))).isEqualTo(ORIGIN);
        assertThat(VapidWebPushSender.origin(URI.create("https://PUSH.Example.COM:443/a/b")))
                .isEqualTo("https://push.example.com:443");
        assertThat(VapidWebPushSender.origin(URI.create("http://push.example.com/a"))).isNull();
    }

    private static PushSubscription subscription(String endpoint) {
        PushSubscription row = new PushSubscription();
        row.setUserId(UUID.randomUUID());
        row.setEndpointUrl(endpoint);
        row.setP256dh("BP-public-key-placeholder");
        row.setAuth("auth-placeholder");
        return row;
    }
}
