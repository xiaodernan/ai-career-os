package com.careeros.ai;

import static org.assertj.core.api.Assertions.assertThat;

import com.careeros.common.RequestIdFilter;
import com.careeros.config.AppProperties;
import com.sun.net.httpserver.HttpServer;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.slf4j.MDC;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

/**
 * The id has to survive the hop onto the relay's own thread.
 *
 * <p>The SSE relay hands the upstream read to a task executor, and MDC is a
 * thread-local: a filter that sets it on the request thread leaves the worker
 * with nothing. The stream is also where tracing matters most -- a stuck turn is
 * exactly the report that arrives with an id and nothing else.
 */
class SseRelayServiceTest {

    private HttpServer server;
    private ExecutorService upstreamServerThread;
    private ExecutorService worker;
    private SseRelayService service;
    private final List<String> requestIds = new CopyOnWriteArrayList<>();
    private final AtomicInteger handled = new AtomicInteger();

    @BeforeEach
    void setUp() throws Exception {
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        upstreamServerThread = Executors.newSingleThreadExecutor();
        server.setExecutor(upstreamServerThread);
        server.createContext("/internal/stream", exchange -> {
            requestIds.add(exchange.getRequestHeaders().getFirst("X-Request-Id"));
            byte[] body = "event: done\ndata: {}\n\n".getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().add("Content-Type", "text/event-stream");
            exchange.sendResponseHeaders(200, body.length);
            exchange.getResponseBody().write(body);
            exchange.close();
            handled.incrementAndGet();
        });
        server.start();

        AppProperties props = new AppProperties();
        props.getInternal().setToken("test-token");
        props.getAiService().setBaseUrl("http://127.0.0.1:" + server.getAddress().getPort());
        worker = Executors.newSingleThreadExecutor();
        service = new SseRelayService(props, worker::execute);
    }

    @AfterEach
    void tearDown() {
        server.stop(0);
        upstreamServerThread.shutdownNow();
        worker.shutdownNow();
    }

    private void awaitUpstream() throws Exception {
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(10);
        while (handled.get() == 0 && System.nanoTime() < deadline) {
            Thread.sleep(10);
        }
        assertThat(handled.get()).isEqualTo(1);
    }

    @Test
    void theRequestsIdReachesTheStreamOnAnotherThread() throws Exception {
        MDC.put(RequestIdFilter.MDC_KEY, "edge-7c1d4f9a");
        try {
            SseEmitter emitter = service.relay(UUID.randomUUID(), UUID.randomUUID());
            awaitUpstream();
            assertThat(requestIds).containsExactly("edge-7c1d4f9a");
            emitter.complete();
        } finally {
            MDC.remove(RequestIdFilter.MDC_KEY);
        }
        // The worker is pooled: the next task on it must not see this request's id.
        assertThat(worker.submit(() -> MDC.get(RequestIdFilter.MDC_KEY)).get(5, TimeUnit.SECONDS))
                .isNull();
    }

    @Test
    void aRelayOutsideARequestSendsNoId() throws Exception {
        service.consume(UUID.randomUUID(), UUID.randomUUID(), (event, data) -> { });
        awaitUpstream();
        assertThat(requestIds).hasSize(1).containsOnlyNulls();
    }
}
