package com.careeros.conversation.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.ArgumentMatchers.anyMap;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.ai.AiServiceClient;
import com.careeros.ai.SseRelayService;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.conversation.dto.ConversationDtos.ChatResponse;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.core.task.TaskExecutor;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

/**
 * The streaming copilot turn, checked against the claims it makes rather than against its code:
 * every frame before the answer reaches the client, the answer itself is stored on this thread
 * (not in the browser), and a turn that fails says so instead of leaving a reader waiting on a
 * stream that will never close.
 *
 * <p>The relay is a mock that replays scripted frames — the network read is SseRelayService's
 * own contract — so what is under test here is the sink-side: forward, intercept, persist.
 */
class CopilotStreamServiceTest {

    private static final UUID USER = UUID.randomUUID();
    private static final UUID CONVERSATION = UUID.randomUUID();
    private static final UUID TASK = UUID.randomUUID();
    private static final String MESSAGE = "which project should I lead with?";

    private ConversationService conversations;
    private AiServiceClient ai;
    private SseRelayService relay;
    private CopilotStreamService service;

    @BeforeEach
    void setUp() {
        conversations = mock(ConversationService.class);
        ai = mock(AiServiceClient.class);
        relay = mock(SseRelayService.class);
        service = new CopilotStreamService(conversations, ai, relay, new ObjectMapper(),
                (TaskExecutor) Runnable::run);

        when(conversations.beginTurn(USER, CONVERSATION, MESSAGE))
                .thenReturn(new ConversationService.ChatTurn(CONVERSATION, List.of()));
        when(ai.copilotChatStart(anyString(), anyList(), any(), anyMap(), any()))
                .thenReturn(Map.of("task_id", TASK.toString(), "run_id", UUID.randomUUID().toString()));
        when(conversations.persistTurn(eq(CONVERSATION), eq(USER), eq(MESSAGE), anyMap()))
                .thenReturn(new ChatResponse(CONVERSATION, UUID.randomUUID(), UUID.randomUUID(),
                        "Grounded answer.", List.of(), List.of(), List.of(), UUID.randomUUID()));
    }

    /** Make the relay hand the listener these frames, then close the way the upstream does. */
    private void relayFrames(String... nameAndData) throws Exception {
        doAnswer(inv -> {
            SseRelayService.FrameListener listener = inv.getArgument(2);
            for (int i = 0; i < nameAndData.length; i += 2) {
                listener.onFrame(nameAndData[i], nameAndData[i + 1]);
            }
            return null;
        }).when(relay).consume(any(), any(), any());
    }

    private RecordingSink run() {
        RecordingSink sink = new RecordingSink();
        service.run(USER, CONVERSATION, MESSAGE, Map.of(), sink);
        return sink;
    }

    private static final class RecordingSink implements CopilotStreamService.Sink {
        private final List<String[]> frames = new ArrayList<>();
        private boolean closed;

        @Override
        public void send(String event, String data) {
            frames.add(new String[]{event, data});
        }

        @Override
        public void close() {
            closed = true;
        }

        List<String> events() {
            return frames.stream().map(f -> f[0]).toList();
        }

        String payloadOf(String event) {
            return frames.stream().filter(f -> f[0].equals(event)).findFirst().orElseThrow()[1];
        }
    }

    @Test
    void everyFrameBeforeTheAnswerIsRelayedToTheClientInOrder() throws Exception {
        relayFrames("status", "{\"step\":\"Thinking\"}",
                "token", "{\"text\":\"Lead \"}",
                "ping", "{}",
                "token", "{\"text\":\"with the ledger.\"}",
                "done", "{\"result\":{\"answer\":\"Lead with the ledger.\"}}");

        RecordingSink sink = run();

        // the keep-alive is dropped: it reports a quiet run, not a step of the answer
        assertThat(sink.events()).containsExactly("status", "token", "token", "done");
        assertThat(sink.payloadOf("token")).isEqualTo("{\"text\":\"Lead \"}");
        assertThat(sink.payloadOf("status")).isEqualTo("{\"step\":\"Thinking\"}");
    }

    @Test
    void theAnswerIsStoredOnTheServerAndTheClientReadsTheStoredTurn() throws Exception {
        relayFrames("done", "{\"result\":{\"answer\":\"Grounded answer.\",\"sources\":[],"
                + "\"artifacts\":[],\"actions\":[],\"run_id\":\"" + UUID.randomUUID() + "\"}}");

        RecordingSink sink = run();

        @SuppressWarnings("unchecked")
        ArgumentCaptor<Map<String, Object>> outcome = ArgumentCaptor.forClass(Map.class);
        verify(conversations).persistTurn(eq(CONVERSATION), eq(USER), eq(MESSAGE), outcome.capture());
        assertThat(outcome.getValue()).containsEntry("answer", "Grounded answer.");

        // the closing frame is the ChatResponse, not ai-service's Outcome: the browser reads the
        // same shape the blocking route answers with, ids included, so one reader serves both.
        String done = sink.payloadOf("done");
        assertThat(done).contains("\"conversationId\"").contains("\"assistantMessageId\"")
                .contains("\"Grounded answer.\"");
        assertThat(sink.closed).isTrue();
    }

    @Test
    void aFailedTurnIsAnErrorFrameAndStoresNothing() throws Exception {
        relayFrames("status", "{\"step\":\"Thinking\"}",
                "error", "{\"error\":\"agent run failed: provider timeout\"}");

        RecordingSink sink = run();

        assertThat(sink.events()).containsExactly("status", "error");
        assertThat(sink.payloadOf("error")).contains("provider timeout");
        verify(conversations, never()).persistTurn(any(), any(), any(), anyMap());
    }

    @Test
    void aStreamThatEndsWithoutAnAnswerSaysSoInsteadOfHangingSilently() throws Exception {
        relayFrames("status", "{\"step\":\"Thinking\"}");

        RecordingSink sink = run();

        assertThat(sink.events()).containsExactly("status", "error");
        assertThat(sink.payloadOf("error")).contains("ended before it produced an answer");
        verify(conversations, never()).persistTurn(any(), any(), any(), anyMap());
        assertThat(sink.closed).isTrue();
    }

    @Test
    void anAiServiceThatCannotStartTheTurnLeavesAReadableError() {
        when(ai.copilotChatStart(anyString(), anyList(), any(), anyMap(), any()))
                .thenThrow(new ApiException(ApiErrorCode.AI_SERVICE_UNAVAILABLE, "AI service request failed"));

        RecordingSink sink = run();

        assertThat(sink.events()).containsExactly("error");
        assertThat(sink.payloadOf("error")).contains("AI service request failed");
        verify(conversations, never()).persistTurn(any(), any(), any(), anyMap());
    }

    @Test
    void aTurnWhoseTaskIdNeverArrivesIsAnErrorNotAWaitForever() throws Exception {
        when(ai.copilotChatStart(anyString(), anyList(), any(), anyMap(), any()))
                .thenReturn(Map.of("run_id", UUID.randomUUID().toString()));

        RecordingSink sink = run();

        assertThat(sink.events()).containsExactly("error");
        assertThat(sink.payloadOf("error")).contains("without a task id");
        verify(relay, never()).consume(any(), any(), any());
    }

    /**
     * The claim that separates this from a browser-driven design: a reader that goes away stops
     * the frames, not the turn. The message is stored whether or not anyone is still watching.
     */
    @Test
    void theTurnIsStoredEvenWhenTheBrowserHasGoneAway() throws Exception {
        relayFrames("token", "{\"text\":\"Lead with the ledger.\"}",
                "done", "{\"result\":{\"answer\":\"Lead with the ledger.\"}}");

        SseEmitter goneAway = new SseEmitter() {
            @Override
            public void send(SseEventBuilder builder) throws IOException {
                throw new IOException("broken pipe");
            }
        };
        service.run(USER, CONVERSATION, MESSAGE, Map.of(), CopilotStreamService.emitterSink(goneAway));

        verify(conversations).persistTurn(eq(CONVERSATION), eq(USER), eq(MESSAGE), anyMap());
    }

    @Test
    void theTurnIsStartedWithTheHistoryTheConversationAlreadyHas() throws Exception {
        when(conversations.beginTurn(USER, null, MESSAGE))
                .thenReturn(new ConversationService.ChatTurn(CONVERSATION,
                        List.of(Map.of("role", "user", "content", "earlier"))));
        relayFrames("done", "{\"result\":{\"answer\":\"ok\"}}");

        service.run(USER, null, MESSAGE, Map.of(), new RecordingSink());

        ArgumentCaptor<List> history = ArgumentCaptor.forClass(List.class);
        verify(ai).copilotChatStart(eq(MESSAGE), history.capture(), eq(CONVERSATION), anyMap(), eq(USER));
        assertThat(history.getValue()).hasSize(1);
    }
}
