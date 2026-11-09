package com.careeros.gateway;

import static org.assertj.core.api.Assertions.assertThat;

import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.reactive.server.WebTestClient;

/**
 * The service-to-service surface must not be reachable from the browser (Epic 95).
 *
 * <p>The backend authenticates `/api/internal/**` with a shared token rather than a user
 * session, because its callers are services. The edge routes every `/api/**` path, so
 * without a guard it also lends that surface to whoever opens the browser -- and a shared
 * secret becomes the only thing between a stranger and the internal endpoints. The stub
 * counts hits, so the test proves the request was refused *here* rather than answered
 * downstream with a 403 the backend chose.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class GatewayInternalSurfaceTest {

    private static final AtomicInteger INTERNAL_HITS = new AtomicInteger();

    private static final AtomicInteger PUBLIC_HITS = new AtomicInteger();

    private static final HttpServer BACKEND = startBackend();

    private static HttpServer startBackend() {
        try {
            HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
            server.createContext("/api/internal/ping", exchange -> {
                INTERNAL_HITS.incrementAndGet();
                answer(exchange, 200, "internal");
            });
            server.createContext("/api/v1/health", exchange -> {
                PUBLIC_HITS.incrementAndGet();
                answer(exchange, 200, "ok");
            });
            server.start();
            return server;
        } catch (IOException e) {
            throw new ExceptionInInitializerError(e);
        }
    }

    private static void answer(com.sun.net.httpserver.HttpExchange exchange, int status, String text)
            throws IOException {
        byte[] body = text.getBytes(StandardCharsets.UTF_8);
        exchange.sendResponseHeaders(status, body.length);
        try (OutputStream out = exchange.getResponseBody()) {
            out.write(body);
        }
    }

    @DynamicPropertySource
    static void backendUri(DynamicPropertyRegistry registry) {
        registry.add("GATEWAY_BACKEND_URI", () -> "http://127.0.0.1:" + BACKEND.getAddress().getPort());
    }

    @Autowired
    private WebTestClient client;

    @BeforeEach
    void resetHits() {
        INTERNAL_HITS.set(0);
        PUBLIC_HITS.set(0);
    }

    @Test
    void refusesTheInternalSurfaceWithoutCallingTheBackend() {
        client.get().uri("/api/internal/ping")
                .exchange()
                .expectStatus().isForbidden()
                .expectBody()
                .jsonPath("$.error").isEqualTo("internal-surface-not-exposed");

        assertThat(INTERNAL_HITS).hasValue(0);
    }

    @Test
    void alsoRefusesTheBarePrefix() {
        client.get().uri("/api/internal")
                .exchange()
                .expectStatus().isForbidden();

        assertThat(INTERNAL_HITS).hasValue(0);
    }

    @Test
    void leavesThePublicSurfaceAlone() {
        client.get().uri("/api/v1/health")
                .exchange()
                .expectStatus().isOk();

        assertThat(PUBLIC_HITS).hasValue(1);
    }
}
