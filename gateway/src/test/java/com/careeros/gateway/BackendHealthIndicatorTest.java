package com.careeros.gateway;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.reactive.server.WebTestClient;

/**
 * The health line must describe the route's own answer (Epic 99.1).
 *
 * <p>The stub listens on a random port that only the discovery list knows. If the
 * indicator went back to a fixed address, this would probe `localhost:8080`, find
 * nothing, and read DOWN -- the exact state a registry deployment used to report while
 * it was forwarding traffic perfectly.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT, properties = {
        "management.endpoint.health.show-details=always"
})
class BackendHealthIndicatorTest {

    private static final HttpServer BACKEND = startBackend();

    private static HttpServer startBackend() {
        try {
            HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
            server.createContext("/api/v1/health", exchange -> {
                byte[] body = "{\"success\":true,\"data\":{\"status\":\"ok\"},\"error\":null}".getBytes(StandardCharsets.UTF_8);
                exchange.getResponseHeaders().set("Content-Type", "application/json");
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
        registry.add("GATEWAY_BACKEND_URI",
                () -> "http://127.0.0.1:" + BACKEND.getAddress().getPort());
    }

    @Autowired
    private WebTestClient client;

    @Test
    void theProbeResolvesTheSameInstanceTheRouteDoes() {
        client.get().uri("/actuator/health")
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$.components.backend.status").isEqualTo("UP")
                .jsonPath("$.components.backend.details.backendStatus").isEqualTo("ok");
    }
}
