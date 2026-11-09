package com.careeros.gateway;

import static org.assertj.core.api.Assertions.assertThat;

import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.reactive.server.WebTestClient;

/**
 * A header the browser invents must not become a fact downstream (Epic 95).
 *
 * <p>Two headers carry authority the caller did not earn. `X-Internal-Token` is the
 * service-to-service credential -- a browser has no reason to send it, so one that does is
 * probing. `X-Forwarded-*` is a statement about the network path; if the edge appends to a
 * client-supplied chain, the backend's `getRemoteAddr()` and every rate limit keyed off it
 * describe the caller's imagination. The edge is the trust boundary: it removes what
 * arrived and writes what it observed.
 *
 * <p>The stub captures the headers the backend actually receives. `Authorization` is
 * asserted alongside them as the control: stripping must be specific to the two families,
 * not a blanket drop that would break every signed-in call.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class GatewayRequestSanitizerTest {

    private static final AtomicReference<String> INTERNAL_TOKEN = new AtomicReference<>();

    private static final AtomicReference<String> AUTHORIZATION = new AtomicReference<>();

    private static final AtomicReference<String> FORWARDED_FOR = new AtomicReference<>();

    private static final AtomicReference<String> FORWARDED_PROTO = new AtomicReference<>();

    private static final AtomicReference<String> FORWARDED = new AtomicReference<>();

    private static final HttpServer BACKEND = startBackend();

    private static HttpServer startBackend() {
        try {
            HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
            server.createContext("/api/v1/echo", exchange -> {
                INTERNAL_TOKEN.set(exchange.getRequestHeaders().getFirst("X-Internal-Token"));
                AUTHORIZATION.set(exchange.getRequestHeaders().getFirst("Authorization"));
                FORWARDED_FOR.set(exchange.getRequestHeaders().getFirst("X-Forwarded-For"));
                FORWARDED_PROTO.set(exchange.getRequestHeaders().getFirst("X-Forwarded-Proto"));
                FORWARDED.set(exchange.getRequestHeaders().getFirst("Forwarded"));
                byte[] body = "ok".getBytes(StandardCharsets.UTF_8);
                exchange.sendResponseHeaders(200, body.length);
                try (OutputStream out = exchange.getResponseBody()) {
                    out.write(body);
                }
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

    @Autowired
    private WebTestClient client;

    @BeforeEach
    void clearCaptures() {
        INTERNAL_TOKEN.set(null);
        AUTHORIZATION.set(null);
        FORWARDED_FOR.set(null);
        FORWARDED_PROTO.set(null);
        FORWARDED.set(null);
    }

    @Test
    void stripsWhatTheBrowserInventedAndKeepsTheCredentialItWasGiven() {
        client.get().uri("/api/v1/echo")
                .header("Authorization", "Bearer abc123")
                .header("X-Internal-Token", "forged-internal-token")
                .header("Forwarded", "for=203.0.113.9")
                .header("X-Forwarded-For", "203.0.113.9")
                .header("X-Forwarded-Proto", "https")
                .exchange()
                .expectStatus().isOk();

        assertThat(INTERNAL_TOKEN.get()).isNull();
        assertThat(AUTHORIZATION.get()).isEqualTo("Bearer abc123");

        // The edge writes a `Forwarded` header of its own, so the assertion is not
        // "absent" but "the caller's address is not in it": the header that arrives is
        // the edge's observation, never the browser's claim.
        assertThat(FORWARDED.get())
                .as("the edge forwards the path it saw, not the one the caller wrote")
                .isNotNull()
                .contains("127.0.0.1")
                .doesNotContain("203.0.113.9");

        assertThat(FORWARDED_FOR.get())
                .as("the edge writes the path it observed, not the one the caller claimed")
                .isNotNull()
                .contains("127.0.0.1")
                .doesNotContain("203.0.113.9");
        assertThat(FORWARDED_PROTO.get()).isEqualTo("http");
    }
}
