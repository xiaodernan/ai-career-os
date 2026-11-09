package com.careeros.gateway;

import static org.assertj.core.api.Assertions.assertThat;

import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.reactive.server.WebTestClient;

/**
 * A body the edge refuses must never reach the backend (Epic 94).
 *
 * <p>The backend has its own multipart cap, but reaching it means the request has already
 * crossed the network and been handed to a parser. The edge can answer before either, so it
 * should -- and the stub counts the hits, because the status alone cannot say whether the
 * request was stopped here or rejected downstream. The cap is lowered to one kilobyte for
 * this class; the shipped value sits above the backend's own limit so the backend remains
 * the authority on files it would accept.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT,
        properties = {"GATEWAY_MAX_REQUEST_SIZE=1KB"})
class GatewayRequestSizeTest {

    private static final AtomicInteger HITS = new AtomicInteger();

    private static final HttpServer BACKEND = startBackend();

    private static HttpServer startBackend() {
        try {
            HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
            server.createContext("/api/v1/upload", exchange -> {
                HITS.incrementAndGet();
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
    void resetHits() {
        HITS.set(0);
    }

    @Test
    void refusesAnOversizedBodyBeforeItReachesTheBackend() {
        client.post().uri("/api/v1/upload")
                .contentType(MediaType.APPLICATION_OCTET_STREAM)
                .bodyValue(bytes(2048))
                .exchange()
                .expectStatus().isEqualTo(413);

        assertThat(HITS).hasValue(0);
    }

    @Test
    void forwardsABodyUnderTheCap() {
        client.post().uri("/api/v1/upload")
                .contentType(MediaType.APPLICATION_OCTET_STREAM)
                .bodyValue(bytes(512))
                .exchange()
                .expectStatus().isOk();

        assertThat(HITS).hasValue(1);
    }

    private static byte[] bytes(int size) {
        byte[] body = new byte[size];
        Arrays.fill(body, (byte) 'x');
        return body;
    }
}
