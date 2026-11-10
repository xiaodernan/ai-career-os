package com.careeros.gateway;

import static org.assertj.core.api.Assertions.assertThat;

import com.sun.net.httpserver.HttpServer;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.HttpHeaders;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.reactive.server.WebTestClient;

/**
 * One reader's flood is another reader's silence (Epic 89.2).
 *
 * <p>The budget is deliberately tiny so the test can spend it: two tokens over one
 * second. The stub counts what actually reached the backend, because the interesting
 * claim is not the 429 -- it is that the refusal happened at the edge, before any work
 * was forwarded.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT, properties = {
        "GATEWAY_RATE_LIMIT_PER_MINUTE=2",
        "GATEWAY_RATE_LIMIT_PERIOD=1s"
})
class GatewayRateLimitTest {

    private static final AtomicInteger FORWARDED = new AtomicInteger();

    private static final HttpServer BACKEND = startBackend();

    private static HttpServer startBackend() {
        try {
            HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
            server.createContext("/api/v1/health", exchange -> {
                FORWARDED.incrementAndGet();
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

    @Autowired
    private MeterRegistry meterRegistry;

    @BeforeEach
    void resetForwarded() {
        FORWARDED.set(0);
    }

    @Test
    void refusesTheThirdAskWithoutForwardingIt() {
        ask("Bearer alpha").expectStatus().isOk();
        ask("Bearer alpha").expectStatus().isOk();
        ask("Bearer alpha")
                .expectStatus().isEqualTo(429)
                .expectHeader().valueEquals(GatewayRateLimitFilter.RETRY_AFTER, "1")
                .expectBody().jsonPath("$.error").isEqualTo("rate-limited");

        assertThat(FORWARDED).hasValue(2);
    }

    @Test
    void oneSpentIdentityDoesNotSpendAnother() {
        ask("Bearer alpha").expectStatus().isOk();
        ask("Bearer alpha").expectStatus().isOk();
        ask("Bearer alpha").expectStatus().isEqualTo(429);

        ask("Bearer beta").expectStatus().isOk();
    }

    @Test
    void theBudgetRefillsAfterThePeriod() throws InterruptedException {
        ask("Bearer gamma").expectStatus().isOk();
        ask("Bearer gamma").expectStatus().isOk();
        ask("Bearer gamma").expectStatus().isEqualTo(429);

        Thread.sleep(1_100);

        ask("Bearer gamma").expectStatus().isOk();
    }

    @Test
    void countsTheRefusalWithoutNamingTheCaller() {
        double before = refusals();

        ask("Bearer delta").expectStatus().isOk();
        ask("Bearer delta").expectStatus().isOk();
        ask("Bearer delta").expectStatus().isEqualTo(429);

        assertThat(refusals() - before).isEqualTo(1.0);
        assertThat(meterRegistry.find("careeros.gateway.ratelimit.refused").meter().getId().getTags())
                .as("a counter tagged by token hash or address grows one series per caller —\n"
                        + "only the platform-wide application tag is allowed (Epic 108.14)")
                .containsExactly(io.micrometer.core.instrument.Tag.of("application", "career-os-gateway"));
    }

    private double refusals() {
        Counter counter = meterRegistry.find("careeros.gateway.ratelimit.refused").counter();
        return counter == null ? 0.0 : counter.count();
    }

    private WebTestClient.ResponseSpec ask(String authorization) {
        return client.get().uri("/api/v1/health")
                .header(HttpHeaders.AUTHORIZATION, authorization)
                .exchange();
    }
}
