package com.careeros.ai;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;

import com.careeros.config.AppProperties;
import com.sun.net.httpserver.HttpServer;
import java.io.InputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.web.client.RestClient;

/**
 * The bridge to the ai-service, over a real socket.
 *
 * <p>Every other test of this product replaces the ai-service with a fake
 * bean, and that fake is exactly why a real defect hid here for a long time:
 * the mock never builds the request body, so a body that could not be built
 * at all was invisible.
 *
 * <p>The one that hid was {@code Map.of}. It rejects a null value, and
 * {@code source} is a caller's optional field -- so a client that omitted it
 * reached {@code Map.of("payload", feed, "source", null)}, the bridge threw
 * a {@link NullPointerException} before it ever made a request, and the
 * caller got a 500 out of a request it had every right to make. The page
 * that sends the feed always names a source, which is why nobody had seen
 * it; the api was the one that could not answer.
 */
class HttpAiServiceClientTest {

    private HttpServer server;
    private HttpAiServiceClient client;
    private final List<String> bodies = new ArrayList<>();

    @BeforeEach
    void setUp() throws Exception {
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/internal", exchange -> {
            try (InputStream in = exchange.getRequestBody()) {
                bodies.add(new String(in.readAllBytes(), StandardCharsets.UTF_8));
            }
            byte[] answer = "{\"postings\": [], \"count\": 0}".getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().add("Content-Type", "application/json");
            exchange.sendResponseHeaders(200, answer.length);
            exchange.getResponseBody().write(answer);
            exchange.close();
        });
        server.start();

        AppProperties props = new AppProperties();
        props.getInternal().setToken("test-token");
        props.getAiService().setBaseUrl("http://127.0.0.1:" + server.getAddress().getPort());
        client = new HttpAiServiceClient(RestClient.builder(), props);
    }

    @AfterEach
    void tearDown() {
        server.stop(0);
    }

    @Test
    void aFeedWithNoSourceIsStillSent() {
        // The caller's optional field, absent. The bridge has to send the
        // request; it does not get to decide that a null means "no".
        assertThatCode(() -> client.parseFeed("<rss/>", null, UUID.randomUUID()))
                .doesNotThrowAnyException();
        assertThat(bodies).hasSize(1);
        assertThat(bodies.get(0)).contains("\"payload\"").contains("<rss/>");
    }

    @Test
    void aFeedWithASourceIsSentWithIt() {
        client.parseFeed("{\"jobs\": []}", "board", UUID.randomUUID());
        assertThat(bodies).hasSize(1);
        assertThat(bodies.get(0)).contains("\"source\"").contains("board");
    }

    @Test
    void theEngineDecidesTheShapeSoTheBridgeDoesNot() {
        // One route for both shapes: the engine detects the feed's format
        // from the text, which is what the ingestion page promises.
        client.parseFeed("<rss/>", "rss", UUID.randomUUID());
        assertThat(bodies.get(0)).doesNotContain("parse-board");
    }
}
