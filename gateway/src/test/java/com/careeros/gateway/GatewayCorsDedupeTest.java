package com.careeros.gateway;

import static org.assertj.core.api.Assertions.assertThat;

import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.HttpHeaders;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.reactive.server.WebTestClient;

/**
 * Both doors answer CORS, so the browser must still see one answer (Epic 94).
 *
 * <p>The gateway's global CORS configuration and the backend's {@code SecurityConfig} name
 * the same origin, which is the point -- but both also write the header onto the same
 * response. Two {@code Access-Control-Allow-Origin} values are a CORS failure in a browser,
 * not a harmless duplicate: the response the reader asked for is rejected, and each module's
 * tests stay green because each sees only its own half.
 *
 * <p>The stub plays a backend that answers CORS itself. The assertion is on the number of
 * values, not merely on the value: a test that read the first one would pass with the
 * duplicate still there.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class GatewayCorsDedupeTest {

    private static final String ORIGIN = "http://localhost:3000";

    private static final HttpServer BACKEND = startBackend();

    private static HttpServer startBackend() {
        try {
            HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
            server.createContext("/api/v1/cors", exchange -> {
                exchange.getResponseHeaders().set("Access-Control-Allow-Origin", ORIGIN);
                exchange.getResponseHeaders().set("Access-Control-Allow-Credentials", "true");
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

    @Test
    void oneOriginHeaderSurvivesBothDoors() {
        HttpHeaders headers = client.get().uri("/api/v1/cors")
                .header(HttpHeaders.ORIGIN, ORIGIN)
                .exchange()
                .expectStatus().isOk()
                .returnResult(String.class)
                .getResponseHeaders();

        List<String> origins = headers.get(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN);
        assertThat(origins).containsExactly(ORIGIN);
        List<String> credentials = headers.get(HttpHeaders.ACCESS_CONTROL_ALLOW_CREDENTIALS);
        assertThat(credentials).containsExactly("true");
    }
}
