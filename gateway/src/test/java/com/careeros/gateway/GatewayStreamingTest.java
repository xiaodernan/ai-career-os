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
import org.springframework.http.MediaType;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.reactive.server.WebTestClient;

/**
 * A stream must arrive as frames, not as one late body (Epic 93).
 *
 * <p>The copilot's answers are server-sent events, and they now pass through this
 * process. A proxy that buffered the response would still make the test's final string
 * equal -- which is why the stub sends three frames with a pause between them and the
 * assertion is on all three being present in one body. What it cannot prove is
 * <em>when</em> they arrived; that belongs to the browser, where the first frame is the
 * difference between a thinking assistant and a frozen page.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class GatewayStreamingTest {

    private static final HttpServer BACKEND = startBackend();

    private static HttpServer startBackend() {
        try {
            HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
            server.createContext("/api/v1/stream", exchange -> {
                exchange.getResponseHeaders().set("Content-Type", "text/event-stream");
                exchange.sendResponseHeaders(200, 0);
                try (OutputStream body = exchange.getResponseBody()) {
                    for (int frame = 1; frame <= 3; frame++) {
                        body.write(("data: {\"frame\":" + frame + "}\n\n")
                                .getBytes(StandardCharsets.UTF_8));
                        body.flush();
                        Thread.sleep(40);
                    }
                } catch (InterruptedException interrupted) {
                    Thread.currentThread().interrupt();
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
    void forwardsEveryFrameOfAnEventStream() {
        // The body arrives as a Flux of frames, not as one String: WebTestClient hands
        // each flushed SSE frame over separately, so blockLast() sees only the final
        // one. Joining every element is what proves no frame was swallowed.
        List<String> parts = client.get().uri("/api/v1/stream")
                .exchange()
                .expectStatus().isOk()
                .expectHeader().contentTypeCompatibleWith(MediaType.TEXT_EVENT_STREAM)
                .returnResult(String.class)
                .getResponseBody()
                .collectList()
                .block();

        assertThat(parts).isNotNull();
        String body = String.join("", parts);
        assertThat(body).contains("frame\":1", "frame\":2", "frame\":3");
    }
}
