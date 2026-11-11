package com.careeros.gateway;

import static org.assertj.core.api.Assertions.assertThat;

import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.regex.Pattern;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.reactive.server.WebTestClient;

/**
 * Epic 128, pinned at the edge: every /api/** request leaves this process carrying
 * its own deadline -- a budget the caller never sees but the rest of the mesh reads.
 * The contract is a number and a shape: the backend answers with the header set, the
 * engine can state its remaining budget, and no caller gets to hand the mesh an
 * expired or absurd budget as if it were useful information.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class GatewayDeadlineTest {

    private static final HttpServer BACKEND = startBackend();
    private static final List<String> SEEN = new CopyOnWriteArrayList<>();
    private static final Pattern DIGITS = Pattern.compile("\\d{1,15}");

    private static HttpServer startBackend() {
        try {
            HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
            server.createContext("/api/v1/thing", exchange -> {
                SEEN.add(exchange.getRequestHeaders().getFirst(DeadlineHeaderFilter.HEADER));
                byte[] body = "{\"ok\":true}".getBytes(StandardCharsets.UTF_8);
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
    void reset() {
        SEEN.clear();
    }

    @Test
    void aRequestLeavesWithAWellFormedBudget() {
        client.get().uri("/api/v1/thing").exchange().expectStatus().isOk();

        assertThat(SEEN).hasSize(1);
        assertThat(SEEN.get(0)).matches(DIGITS);
        long deadline = Long.parseLong(SEEN.get(0));
        // Within the budget this deployment ships (default 300s), and in the future.
        assertThat(deadline).isGreaterThan(System.currentTimeMillis());
        assertThat(deadline).isLessThanOrEqualTo(System.currentTimeMillis() + 300_000);
    }

    @Test
    void aCallersFutureDeadlineWithinBudgetIsKept() {
        long caller = System.currentTimeMillis() + 30_000;

        client.get().uri("/api/v1/thing")
                .header(DeadlineHeaderFilter.HEADER, String.valueOf(caller))
                .exchange().expectStatus().isOk();

        assertThat(SEEN).containsExactly(String.valueOf(caller));
    }

    @Test
    void aCallersExpiredDeadlineIsReplacedNotForwarded() {
        long expired = System.currentTimeMillis() - 1_000;

        client.get().uri("/api/v1/thing")
                .header(DeadlineHeaderFilter.HEADER, String.valueOf(expired))
                .exchange().expectStatus().isOk();

        assertThat(SEEN).hasSize(1);
        long forwarded = Long.parseLong(SEEN.get(0));
        assertThat(forwarded).isGreaterThan(System.currentTimeMillis());
    }

    @Test
    void garbageFromACallerIsReplacedNotForwarded() {
        client.get().uri("/api/v1/thing")
                .header(DeadlineHeaderFilter.HEADER, "tomorrow")
                .exchange().expectStatus().isOk();

        assertThat(SEEN).hasSize(1);
        assertThat(SEEN.get(0)).matches(DIGITS);
    }
}
