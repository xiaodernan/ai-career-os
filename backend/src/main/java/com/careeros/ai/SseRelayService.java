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

    private void pump(UUID taskId, UUID userId, SseEmitter emitter) {
        try {
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
                emitter.send(SseEmitter.event().name("error").data("upstream status " + response.statusCode()));
                emitter.complete();
                return;
            }
            relayEvents(response.body(), emitter);
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
    private void relayEvents(InputStream body, SseEmitter emitter) throws IOException {
        BufferedReader reader = new BufferedReader(new InputStreamReader(body, StandardCharsets.UTF_8));
        String eventName = null;
        StringBuilder data = new StringBuilder();
        String line;
        while ((line = reader.readLine()) != null) {
            if (line.isEmpty()) {
                if (data.length() > 0) {
                    emitter.send(SseEmitter.event()
                            .name(eventName == null ? "message" : eventName)
                            .data(data.toString()));
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
            emitter.send(SseEmitter.event().name(eventName == null ? "message" : eventName).data(data.toString()));
        }
    }
}
