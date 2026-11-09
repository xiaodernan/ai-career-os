package com.careeros.gateway;

import static org.assertj.core.api.Assertions.assertThat;

import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.reactive.server.WebTestClient;

/**
 * The edge can be identified, can be trusted to say how the caller arrived, and can be
 * scraped (Epic 92).
 *
 * <p>Three small operational facts, each one a stub assertion rather than a promise:
 * the root names the process, the forwarded headers reach the backend so its logs and
 * rate decisions see the browser rather than the gateway, and the HTTP metric that every
 * dashboard expects is exposed.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class GatewayOperationsTest {

    private record Seen(String forwardedFor, String forwardedProto, String forwardedHost) {
    }

    private static final BlockingQueue<Seen> SEEN = new LinkedBlockingQueue<>();

    private static final HttpServer BACKEND = startBackend();

    private static HttpServer startBackend() {
        try {
            HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
            server.createContext("/", exchange -> {
                SEEN.add(new Seen(
                        exchange.getRequestHeaders().getFirst("X-Forwarded-For"),
                        exchange.getRequestHeaders().getFirst("X-Forwarded-Proto"),
                        exchange.getRequestHeaders().getFirst("X-Forwarded-Host")));
                byte[] body = "{\"status\":\"ok\"}".getBytes(StandardCharsets.UTF_8);
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
        registry.add("GATEWAY_BACKEND_URI", () -> "http://127.0.0.1:" + BACKEND.getAddress().getPort());
    }

    @Autowired
    private WebTestClient client;

    @BeforeEach
    void clearSeen() {
        SEEN.clear();
    }

    @Test
    void theRootSaysWhatThisProcessIs() {
        client.get().uri("/")
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$.service").isEqualTo("career-os-gateway")
                .jsonPath("$.api").isEqualTo("/api/**")
                .jsonPath("$.health").isEqualTo("/actuator/health");
    }

    @Test
    void theBackendReceivesHowTheBrowserArrived() {
        client.get().uri("/api/v1/health").exchange().expectStatus().isOk();

        Seen seen = SEEN.poll();
        assertThat(seen).as("the stub should have been asked").isNotNull();
        assertThat(seen.forwardedFor()).isNotBlank();
        assertThat(seen.forwardedProto()).isEqualTo("http");
        assertThat(seen.forwardedHost()).isNotBlank();
    }

    @Test
    void theHttpMetricIsExposedForScraping() {
        client.get().uri("/api/v1/health").exchange().expectStatus().isOk();

        client.get().uri("/actuator/metrics/http.server.requests")
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$.name").isEqualTo("http.server.requests");
    }
}
