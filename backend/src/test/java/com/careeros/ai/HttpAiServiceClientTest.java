package com.careeros.ai;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
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
            String body;
            try (InputStream in = exchange.getRequestBody()) {
                body = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            }
            bodies.add(body);
            // A payload that asks to be refused answers the way the
            // ai-service's typed refusals do; anything else succeeds. The
            // marker rides in the payload, so one context covers both.
            byte[] answer = refusalFor(body).getBytes(StandardCharsets.UTF_8);
            int status = body.contains("REFUSE") ? 400 : 200;
            exchange.getResponseHeaders().add("Content-Type", "application/json");
            exchange.sendResponseHeaders(status, answer.length);
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
    void theWeeklyLetterAsksForItsOwnWindow() {
        // The dashboard's digest keeps the engine's default; the weekly letter (19.4) is about
        // seven days, so it says so instead of inheriting a fortnight and calling a week quiet.
        client.insightDigest(UUID.randomUUID(), List.of(), null, 7);
        assertThat(bodies).hasSize(1);
        assertThat(bodies.get(0)).contains("\"stale_days\":7").doesNotContain("\"locale\"");
    }

    @Test
    void theDashboardDigestKeepsTheEnginesDefaultWindow() {
        client.insightDigest(UUID.randomUUID(), List.of(), null);
        assertThat(bodies.get(0)).contains("\"stale_days\":14");
    }

    @Test
    void thePrintViewCarriesTheRowBodyAndTheReadersLanguage() {
        client.renderResume(UUID.randomUUID(), Map.of("profile", Map.of("name", "Ada")),
                "plain body", "Main", "v2", "zh");
        assertThat(bodies).hasSize(1);
        assertThat(bodies.get(0))
                .contains("\"resume\":{\"profile\":{\"name\":\"Ada\"}}")
                .contains("\"text\":\"plain body\"")
                .contains("\"title\":\"Main\"")
                .contains("\"subtitle\":\"v2\"")
                .contains("\"locale\":\"zh\"");
    }

    @Test
    void aPrintWithNothingToSaySendsAnEmptyBodyRatherThanNulls() {
        // A version can be nullable through and through -- an upload that was never
        // parsed has no structured body and no plaintext. Map.of would refuse the
        // null before the request left, which is the same defect this class exists for.
        assertThatCode(() -> client.renderResume(UUID.randomUUID(), null, null, null, null, null))
                .doesNotThrowAnyException();
        assertThat(bodies.get(0)).contains("\"resume\":{}").doesNotContain("null");
    }

    @Test
    void theEngineDecidesTheShapeSoTheBridgeDoesNot() {
        // One route for both shapes: the engine detects the feed's format
        // from the text, which is what the ingestion page promises.
        client.parseFeed("<rss/>", "rss", UUID.randomUUID());
        assertThat(bodies.get(0)).doesNotContain("parse-board");
    }

    // ---------------- the upstream's refusals ----------------

    @Test
    void aStructuredRefusalKeepsTheUpstreamSentence() {
        // The ai-service answers a typed refusal as
        // {"detail": {"code": ..., "message": ...}}. The code is the
        // upstream's own vocabulary -- this service does not speak it yet --
        // but the sentence is the reader's, and it used to be dropped on the
        // floor because the boundary read detail as a String only.
        ApiException thrown = null;
        try {
            client.parseFeed("REFUSE-STRUCTURED", "rss", UUID.randomUUID());
        } catch (ApiException e) {
            thrown = e;
        }
        assertThat(thrown).isNotNull();
        assertThat(thrown.code()).isEqualTo(ApiErrorCode.AI_SERVICE_BAD_REQUEST);
        assertThat(thrown).hasMessage("invalid feed xml");
    }

    @Test
    void aLegacyStringDetailStillCrosses() {
        assertThatThrownBy(() ->
                client.parseFeed("REFUSE-LEGACY", "rss", UUID.randomUUID()))
                .isInstanceOf(ApiException.class)
                .hasMessage("the legacy sentence");
    }

    @Test
    void aRefusalWithoutASentenceFallsBackRatherThanInventingOne() {
        assertThatThrownBy(() ->
                client.parseFeed("REFUSE-NO-SENTENCE", "rss", UUID.randomUUID()))
                .isInstanceOf(ApiException.class)
                .hasMessage("AI service rejected the request");
    }

    @Test
    void aLongUpstreamSentenceIsCutForTheToast() {
        assertThatThrownBy(() ->
                client.parseFeed("REFUSE-LONG", "rss", UUID.randomUUID()))
                .isInstanceOf(ApiException.class)
                .hasMessage("x".repeat(300) + "\u2026");
    }

    /** The refusal bodies the fake upstream answers, keyed by payload marker. */
    private static String refusalFor(String body) {
        if (body.contains("REFUSE-STRUCTURED")) {
            return "{\"detail\": {\"code\": \"INGEST_FEED_INVALID\", "
                    + "\"message\": \"invalid feed xml\"}}";
        }
        if (body.contains("REFUSE-LEGACY")) {
            return "{\"detail\": \"the legacy sentence\"}";
        }
        if (body.contains("REFUSE-NO-SENTENCE")) {
            return "{\"detail\": {\"code\": \"INGEST_FEED_INVALID\"}}";
        }
        if (body.contains("REFUSE-LONG")) {
            return "{\"detail\": {\"code\": \"X\", \"message\": \""
                    + "x".repeat(400) + "\"}}";
        }
        return "{\"postings\": [], \"count\": 0}";
    }
}
