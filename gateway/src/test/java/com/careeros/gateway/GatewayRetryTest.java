package com.careeros.gateway;

import static org.assertj.core.api.Assertions.assertThat;

import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
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
 * The edge repeats only work that has not begun (Epic 89.1).
 *
 * <p>A GET that met a server error or a connection that never opened is safe to ask
 * again once; a POST may already have changed something, and the backend cannot undo
 * it. The stub counts attempts so the contract is a number, not an intention: the read
 * is asked twice, the write exactly once.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class GatewayRetryTest {

    private static final AtomicInteger READ_ATTEMPTS = new AtomicInteger();
    private static final AtomicInteger WRITE_ATTEMPTS = new AtomicInteger();

    private static final HttpServer BACKEND = startBackend();

    private static HttpServer startBackend() {
        try {
            HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
            server.createContext("/api/v1/flaky", exchange -> {
                int attempt = READ_ATTEMPTS.incrementAndGet();
                if (attempt == 1) {
                    exchange.sendResponseHeaders(500, -1);
                    exchange.close();
                    return;
                }
                byte[] body = "{\"ok\":true}".getBytes(StandardCharsets.UTF_8);
                exchange.getResponseHeaders().set("Content-Type", "application/json");
                exchange.sendResponseHeaders(200, body.length);
                exchange.getResponseBody().write(body);
                exchange.close();
            });
            server.createContext("/api/v1/write", exchange -> {
                WRITE_ATTEMPTS.incrementAndGet();
                exchange.sendResponseHeaders(500, -1);
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

    @Autowired
    private WebTestClient client;

    @BeforeEach
    void resetCounters() {
        READ_ATTEMPTS.set(0);
        WRITE_ATTEMPTS.set(0);
    }

    @Test
    void asksTheReadAgainAfterAServerError() {
        client.get().uri("/api/v1/flaky")
                .exchange()
                .expectStatus().isOk()
                .expectBody().jsonPath("$.ok").isEqualTo(true);

        assertThat(READ_ATTEMPTS).hasValue(2);
    }

    @Test
    void neverRepeatsAWriteThatMayAlreadyHaveLanded() {
        client.post().uri("/api/v1/write")
                .exchange()
                .expectStatus().isEqualTo(500);

        assertThat(WRITE_ATTEMPTS).hasValue(1);
    }
}
