package com.careeros.conversation.service;

import com.careeros.ai.AiServiceClient;
import com.careeros.ai.SseRelayService;
import com.careeros.common.Json;
import com.careeros.conversation.dto.ConversationDtos.ChatResponse;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.time.Duration;
import java.util.Map;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.task.TaskExecutor;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

/**
 * The copilot's streaming turn: {@code POST /copilot/chat/stream} answers with an event stream
 * while the agent works, so the reply is written on screen as it is written by the model.
 *
 * <p>ai-service runs the turn as a background task; this service starts it, relays its frames, and
 * intercepts the last one. {@code done} carries ai-service's {@code Outcome}, and what the client
 * gets instead is the same {@link ChatResponse} the blocking route answers with — after
 * {@link ConversationService#persistTurn} has stored both messages. <b>The turn is persisted on
 * this thread, not in the browser</b>: closing the tab mid-answer must not lose a message the
 * model already produced, and it does not, because the pump keeps reading to {@code done} whether
 * or not anyone is still listening.
 *
 * <p>Tokens are provisional (the loop may still call a tool after emitting some) and
 * {@code answer} in the final frame is what actually got stored — the same rule the ai-service
 * turn itself documents.
 */
@Service
public class CopilotStreamService {

    private static final Logger log = LoggerFactory.getLogger(CopilotStreamService.class);
    /** Long enough for an eight-step turn with tool calls; the relay above uses the same bound. */
    private static final long TIMEOUT_MS = Duration.ofMinutes(10).toMillis();

    /** Where frames go: an {@link SseEmitter} in production, a recording list in tests. */
    public interface Sink {
        void send(String event, String data);

        void close();
    }

    private final ConversationService conversations;
    private final AiServiceClient ai;
    private final SseRelayService relay;
    private final ObjectMapper json;
    private final TaskExecutor executor;

    public CopilotStreamService(ConversationService conversations, AiServiceClient ai,
                                SseRelayService relay, ObjectMapper json, TaskExecutor applicationTaskExecutor) {
        this.conversations = conversations;
        this.ai = ai;
        this.relay = relay;
        this.json = json;
        this.executor = applicationTaskExecutor;
    }

    public SseEmitter stream(UUID userId, UUID conversationId, String message, Map<String, Object> context) {
        SseEmitter emitter = new SseEmitter(TIMEOUT_MS);
        Sink sink = emitterSink(emitter);
        executor.execute(() -> run(userId, conversationId, message, context, sink));
        return emitter;
    }

    /**
     * One turn, start to finish, on the calling thread. Everything the client can fail on — a
     * missing conversation, an ai-service outage, a turn that dies — leaves this method as an
     * {@code error} frame rather than an HTTP status, because by the time we know, the response
     * is already a stream.
     */
    void run(UUID userId, UUID conversationId, String message, Map<String, Object> context, Sink sink) {
        try {
            ConversationService.ChatTurn turn = conversations.beginTurn(userId, conversationId, message);
            Map<String, Object> started = ai.copilotChatStart(message, turn.history(),
                    turn.conversationId(), context, userId);
            UUID taskId = Json.uuidOrNull(started, "task_id");
            if (taskId == null) {
                throw new IllegalStateException("the AI service started a turn without a task id");
            }
            boolean[] finished = {false};
            relay.consume(taskId, userId, (event, data) -> {
                switch (event) {
                    case "done" -> {
                        finished[0] = true;
                        persist(turn.conversationId(), userId, message, data, sink);
                    }
                    case "error" -> {
                        finished[0] = true;
                        sink.send("error", data);
                    }
                    // the task bus's 15s keep-alive: it says the run is alive, nothing else,
                    // and a browser that renders it would flash a blank frame every 15 seconds.
                    case "ping" -> { }
                    default -> sink.send(event, data);
                }
            });
            if (!finished[0]) {
                fail(sink, "the turn ended before it produced an answer");
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            fail(sink, "the turn was interrupted");
        } catch (Exception e) {
            log.warn("streaming copilot turn failed for user {}", userId, e);
            fail(sink, reason(e));
        } finally {
            sink.close();
        }
    }

    /** Store the turn, then hand the client the reply the blocking route would have answered. */
    private void persist(UUID conversationId, UUID userId, String message, String doneData, Sink sink)
            throws Exception {
        Map<String, Object> payload = Json.obj(json.readValue(doneData, Map.class));
        if (!payload.containsKey("result")) {
            fail(sink, Json.strOr(payload, "error", "the turn finished without an answer"));
            return;
        }
        ChatResponse reply = conversations.persistTurn(conversationId, userId, message,
                Json.obj(payload.get("result")));
        sink.send("done", json.writeValueAsString(reply));
    }

    private void fail(Sink sink, String reason) {
        try {
            sink.send("error", json.writeValueAsString(Map.of("error", reason)));
        } catch (Exception e) {  // a message we built ourselves, so this one is not the story
            sink.send("error", "{\"error\":\"the turn failed\"}");
        }
    }

    /** The first line only: an exception message can carry a URL or a whole stack frame. */
    private static String reason(Exception e) {
        String message = e.getMessage();
        if (message == null || message.isBlank()) {
            return e.getClass().getSimpleName();
        }
        String firstLine = message.split("\\R", 2)[0];
        return firstLine.length() > 300 ? firstLine.substring(0, 300) : firstLine;
    }

    /**
     * A sink over the response body that survives the client. Once the browser is gone (tab
     * closed, emitter timed out) sending fails for the rest of the turn — so the failure is
     * remembered here and every later frame is dropped, while the run itself continues to its
     * {@code done}: persistence is this thread's job, not the reader's.
     */
    static Sink emitterSink(SseEmitter emitter) {
        return new Sink() {
            private boolean clientGone;

            @Override
            public void send(String event, String data) {
                if (clientGone) {
                    return;
                }
                try {
                    emitter.send(SseEmitter.event().name(event).data(data));
                } catch (IOException | IllegalStateException e) {
                    clientGone = true;
                    log.debug("copilot stream lost its client: {}", e.getMessage());
                }
            }

            @Override
            public void close() {
                if (clientGone) {
                    return;
                }
                clientGone = true;
                try {
                    emitter.complete();
                } catch (Exception e) {
                    log.debug("completing the copilot stream failed: {}", e.getMessage());
                }
            }
        };
    }
}
