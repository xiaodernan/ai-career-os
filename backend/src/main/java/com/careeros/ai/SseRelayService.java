package com.careeros.ai;

import com.careeros.config.AppProperties;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.task.TaskExecutor;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

/**
 * SSE passthrough: backend authenticates the user (JWT filter), then relays the ai-service
 * internal stream with the shared internal token, so the AI service is never exposed directly.
 */
@Service
public class SseRelayService {

    private static final Logger log = LoggerFactory.getLogger(SseRelayService.class);
    private static final Duration RELAY_TIMEOUT = Duration.ofMinutes(10);

    private final HttpClient httpClient;
    private final AppProperties props;
    private final TaskExecutor taskExecutor;

    public SseRelayService(AppProperties props, TaskExecutor applicationTaskExecutor) {
        this.props = props;
        this.taskExecutor = applicationTaskExecutor;
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(5))
                .version(HttpClient.Version.HTTP_1_1)
                .build();
    }

    public SseEmitter relay(UUID taskId, UUID userId) {
        SseEmitter emitter = new SseEmitter(RELAY_TIMEOUT.toMillis());
        taskExecutor.execute(() -> pump(taskId, userId, emitter));
        emitter.onCompletion(() -> log.debug("SSE relay completed for task {}", taskId));
        return emitter;
    }

    /** One frame of an upstream event stream: its name and the raw `data` payload. */
    @FunctionalInterface
    public interface FrameListener {
        void onFrame(String event, String data) throws Exception;
    }

    /**
     * Read a task's stream on the calling thread, handing every frame to {@code listener}, and
     * return when the upstream closes (right after its own {@code done} / {@code error} frame).
     *
     * <p>Relaying to an emitter and consuming a turn's frames are the same read with different
     * sinks: the copilot stream intercepts {@code done} to persist the turn, which it cannot do
     * through {@link #relay}. One parser, so the two paths cannot disagree about what a frame is.
     */
    public void consume(UUID taskId, UUID userId, FrameListener listener) throws Exception {
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(props.getAiService().getBaseUrl() + "/internal/stream/" + taskId))
                .timeout(RELAY_TIMEOUT)
                .header("X-Internal-Token", props.getInternal().getToken())
                .header("X-User-Id", userId.toString())
                .header("Accept", "text/event-stream")
                .GET()
                .build();
        HttpResponse<InputStream> response = httpClient.send(request, HttpResponse.BodyHandlers.ofInputStream());
        if (response.statusCode() != 200) {
            listener.onFrame("error", "upstream status " + response.statusCode());
            return;
        }
        readFrames(response.body(), listener);
    }

    private void pump(UUID taskId, UUID userId, SseEmitter emitter) {
        try {
            consume(taskId, userId, (event, data) ->
                    emitter.send(SseEmitter.event().name(event).data(data)));
            emitter.complete();
        } catch (IOException e) {
            // Client disconnect or upstream drop — close quietly.
            log.debug("SSE relay ended for task {}: {}", taskId, e.getMessage());
            emitter.completeWithError(e);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            emitter.completeWithError(e);
        } catch (Exception e) {
            log.warn("SSE relay failed for task {}", taskId, e);
            emitter.completeWithError(e);
        }
    }

    /** Minimal event-stream parser: forwards (event, data) pairs terminated by a blank line. */
    private void readFrames(InputStream body, FrameListener listener) throws Exception {
        BufferedReader reader = new BufferedReader(new InputStreamReader(body, StandardCharsets.UTF_8));
        String eventName = null;
        StringBuilder data = new StringBuilder();
        String line;
        while ((line = reader.readLine()) != null) {
            if (line.isEmpty()) {
                if (data.length() > 0) {
                    listener.onFrame(eventName == null ? "message" : eventName, data.toString());
                    data.setLength(0);
                    eventName = null;
                }
                continue;
            }
            if (line.startsWith(":")) {
                continue; // comment / keep-alive
            }
            if (line.startsWith("event:")) {
                eventName = line.substring(6).trim();
            } else if (line.startsWith("data:")) {
                if (data.length() > 0) {
                    data.append('\n');
                }
                String value = line.substring(5);
                data.append(value.startsWith(" ") ? value.substring(1) : value);
            }
        }
        if (data.length() > 0) {
            listener.onFrame(eventName == null ? "message" : eventName, data.toString());
        }
    }
}
