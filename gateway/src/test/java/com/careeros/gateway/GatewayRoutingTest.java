package com.careeros.gateway;

import static org.assertj.core.api.Assertions.assertThat;

import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.HttpHeaders;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.reactive.server.WebTestClient;

/**
 * The edge forwards what it promises and adds exactly one thing (Epic 88).
 *
 * <p>A real JDK HTTP server stands in for the backend: the assertions are about the bytes
 * that leave the gateway, not about a mocked handler agreeing with itself. No Docker, no
 * network beyond the loopback, so the suite runs with the same offline harness as the
 * rest of the repository.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class GatewayRoutingTest {

    private record Recorded(String method, String uri, String authorization, String requestId, String traceparent) {
    }

    private static final BlockingQueue<Recorded> REQUESTS = new LinkedBlockingQueue<>();

    private static final HttpServer BACKEND = startBackend();

    private static HttpServer startBackend() {
        try {
            HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
            server.createContext("/", exchange -> {
                REQUESTS.add(new Recorded(
                        exchange.getRequestMethod(),
                        exchange.getRequestURI().toString(),
                        exchange.getRequestHeaders().getFirst(HttpHeaders.AUTHORIZATION),
                        exchange.getRequestHeaders().getFirst(RequestIdFilter.HEADER),
                        exchange.getRequestHeaders().getFirst(RequestIdFilter.TRACEPARENT_HEADER)));
                byte[] body = ("{\"path\":\"" + exchange.getRequestURI().getPath() + "\"}")
                        .getBytes(StandardCharsets.UTF_8);
                exchange.getResponseHeaders().set(HttpHeaders.CONTENT_TYPE, "application/json");
                exchange.sendResponseHeaders(200, body.length);
                exchange.getResponseBody().write(body);
                exchange.close();
            });
            server.start();
            return server;
        } catch (IOException e) {
            throw new ExceptionInInitializerError(e);
        }
    }

    @DynamicPropertySource
    static void backendUri(DynamicPropertyRegistry registry) {
        registry.add("GATEWAY_BACKEND_URI", () -> "http://127.0.0.1:" + BACKEND.getAddress().getPort());
    }

    @AfterAll
    static void stopBackend() {
        BACKEND.stop(0);
    }

    @Autowired
    private WebTestClient client;

    @BeforeEach
    void clearRequests() {
        REQUESTS.clear();
    }

    @Test
    void forwardsThePathQueryAndAuthorizationHeader() {
        client.get().uri("/api/v1/jobs?probe=1")
                .header(HttpHeaders.AUTHORIZATION, "Bearer token-123")
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$.path").isEqualTo("/api/v1/jobs");

        Recorded recorded = poll();
        assertThat(recorded.method()).isEqualTo("GET");
        assertThat(recorded.uri()).isEqualTo("/api/v1/jobs?probe=1");
        assertThat(recorded.authorization()).isEqualTo("Bearer token-123");
    }

    @Test
    void mintsOneIdAndCarriesItToTheBackendAndTheBrowser() {
        String id = client.get().uri("/api/v1/health")
                .exchange()
                .expectStatus().isOk()
                .returnResult(String.class)
                .getResponseHeaders()
                .getFirst(RequestIdFilter.HEADER);

        assertThat(id).matches("[A-Za-z0-9][A-Za-z0-9._-]{7,63}");
        assertThat(poll().requestId()).isEqualTo(id);
    }

    @Test
    void keepsAnIdTheCallerAlreadyMinted() {
        String inbound = "trace-abc-123";

        client.get().uri("/api/v1/health")
                .header(RequestIdFilter.HEADER, inbound)
                .exchange()
                .expectStatus().isOk()
                .expectHeader().valueEquals(RequestIdFilter.HEADER, inbound);

        assertThat(poll().requestId()).isEqualTo(inbound);
    }

    @Test
    void replacesAnIdThatCouldNotBeLoggedSafely() {
        String shortId = "short";

        String answered = client.get().uri("/api/v1/health")
                .header(RequestIdFilter.HEADER, shortId)
                .exchange()
                .expectStatus().isOk()
                .returnResult(String.class)
                .getResponseHeaders()
                .getFirst(RequestIdFilter.HEADER);

        assertThat(answered).isNotEqualTo(shortId).matches("[A-Za-z0-9][A-Za-z0-9._-]{7,63}");
        assertThat(poll().requestId()).isEqualTo(answered);
    }

    @Test
    void doesNotSendWhatIsNotAnApiRoute() {
        client.get().uri("/not-an-api").exchange().expectStatus().isNotFound();

        assertThat(REQUESTS).isEmpty();
    }

    @Test
    void answersThePreflightWithTheSamePolicyAsTheBackend() {
        client.options().uri("/api/v1/jobs")
                .header(HttpHeaders.ORIGIN, "http://localhost:3000")
                .header(HttpHeaders.ACCESS_CONTROL_REQUEST_METHOD, "POST")
                .header(HttpHeaders.ACCESS_CONTROL_REQUEST_HEADERS, "authorization,content-type")
                .exchange()
                .expectStatus().isOk()
                .expectHeader().valueEquals(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN, "http://localhost:3000");

        assertThat(REQUESTS).isEmpty();
    }

    @Test
    void mintsTraceparentAndForwardsItToBackend() {
        // epic 101: correlation crosses the edge
        String tp = client.get().uri("/api/v1/health")
                .exchange()
                .expectStatus().isOk()
                .returnResult(String.class)
                .getResponseHeaders()
                .getFirst(RequestIdFilter.TRACEPARENT_HEADER);

        assertThat(tp).matches("00-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}");
        assertThat(poll().traceparent()).isEqualTo(tp);
    }

    @Test
    void preservesValidInboundTraceparent() {
        String inbound = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01";
        client.get().uri("/api/v1/health")
                .header(RequestIdFilter.TRACEPARENT_HEADER, inbound)
                .exchange()
                .expectStatus().isOk()
                .expectHeader().valueEquals(RequestIdFilter.TRACEPARENT_HEADER, inbound);

        assertThat(poll().traceparent()).isEqualTo(inbound);
    }

    @Test
    void replacesInvalidTraceparent() {
        String inbound = "not-a-trace";
        String answered = client.get().uri("/api/v1/health")
                .header(RequestIdFilter.TRACEPARENT_HEADER, inbound)
                .exchange()
                .expectStatus().isOk()
                .returnResult(String.class)
                .getResponseHeaders()
                .getFirst(RequestIdFilter.TRACEPARENT_HEADER);

        assertThat(answered).isNotEqualTo(inbound).matches("00-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}");
        assertThat(poll().traceparent()).isEqualTo(answered);
    }

    private static Recorded poll() {
        Recorded recorded = REQUESTS.poll();
        assertThat(recorded).as("the backend should have been asked").isNotNull();
        return recorded;
    }
}
