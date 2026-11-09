package com.careeros.gateway;

import static org.assertj.core.api.Assertions.assertThat;

import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.HttpHeaders;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.reactive.server.WebTestClient;

/**
 * The headers are on the refusals too (Epic 97).
 *
 * <p>A `nosniff` on a 200 is easy; the response a browser is most likely to render by
 * accident is the one that was refused. The internal-surface guard answers before the
 * route runs, so this class asks both a forwarded path and a refused one and reads the
 * same three headers from each -- which is what proves the filter wraps the chain rather
 * than decorating its successes.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class GatewaySecurityHeadersTest {

    private static final HttpServer BACKEND = startBackend();

    private static HttpServer startBackend() {
        try {
            HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
            server.createContext("/api/v1/headers", exchange -> {
                byte[] body = "{\"ok\":true}".getBytes(StandardCharsets.UTF_8);
                exchange.getResponseHeaders().set("Content-Type", "application/json");
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

    @Test
    void aForwardedAnswerCarriesThem() {
        HttpHeaders headers = client.get().uri("/api/v1/headers")
                .exchange()
                .expectStatus().isOk()
                .returnResult(String.class)
                .getResponseHeaders();

        assertTheHeaders(headers);
    }

    @Test
    void aRefusalCarriesThemToo() {
        HttpHeaders headers = client.get().uri("/api/internal/ping")
                .exchange()
                .expectStatus().isForbidden()
                .returnResult(String.class)
                .getResponseHeaders();

        assertTheHeaders(headers);
    }

    private static void assertTheHeaders(HttpHeaders headers) {
        assertThat(headers.getFirst("X-Content-Type-Options")).isEqualTo("nosniff");
        assertThat(headers.getFirst("X-Frame-Options")).isEqualTo("DENY");
        assertThat(headers.getFirst("Referrer-Policy")).isEqualTo("no-referrer");
    }
}
