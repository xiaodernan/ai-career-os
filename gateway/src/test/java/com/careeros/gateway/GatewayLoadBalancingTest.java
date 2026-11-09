package com.careeros.gateway;

import static org.assertj.core.api.Assertions.assertThat;

import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.reactive.server.WebTestClient;

/**
 * Two backend addresses become one route (Epic 91.1).
 *
 * <p>The route says `lb://backend`; the simple discovery client holds the instance
 * list and the gateway's load-balancer filter picks one per request. The stub pair
 * answers with their own names, so the assertion can say what a reader would see: the
 * edge used both doors, not just the first one it was configured with.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class GatewayLoadBalancingTest {

    private static final AtomicInteger FIRST_HITS = new AtomicInteger();
    private static final AtomicInteger SECOND_HITS = new AtomicInteger();

    private static final HttpServer FIRST = start("first", FIRST_HITS);
    private static final HttpServer SECOND = start("second", SECOND_HITS);

    private static HttpServer start(String name, AtomicInteger hits) {
        try {
            HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
            server.createContext("/", exchange -> {
                hits.incrementAndGet();
                byte[] body = ("{\"instance\":\"" + name + "\"}").getBytes(StandardCharsets.UTF_8);
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
    static void instances(DynamicPropertyRegistry registry) {
        registry.add("GATEWAY_BACKEND_URI",
                () -> "http://127.0.0.1:" + FIRST.getAddress().getPort());
        registry.add("spring.cloud.discovery.client.simple.instances.backend[0].uri",
                () -> "http://127.0.0.1:" + FIRST.getAddress().getPort());
        registry.add("spring.cloud.discovery.client.simple.instances.backend[1].uri",
                () -> "http://127.0.0.1:" + SECOND.getAddress().getPort());
    }

    @Autowired
    private WebTestClient client;

    @BeforeEach
    void reset() {
        FIRST_HITS.set(0);
        SECOND_HITS.set(0);
    }

    @Test
    void spreadsReadsAcrossBothConfiguredInstances() {
        List<String> answers = new ArrayList<>();
        for (int i = 0; i < 4; i++) {
            answers.add(client.get().uri("/api/v1/health")
                    .exchange()
                    .expectStatus().isOk()
                    .returnResult(String.class)
                    .getResponseBody()
                    .blockFirst());
        }

        assertThat(answers).contains("{\"instance\":\"first\"}", "{\"instance\":\"second\"}");
        assertThat(FIRST_HITS).hasValue(2);
        assertThat(SECOND_HITS).hasValue(2);
    }
}
