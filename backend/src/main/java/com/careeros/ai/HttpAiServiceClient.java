package com.careeros.ai;

import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.config.AppProperties;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

/**
 * Typed wrapper around the ai-service /internal/* endpoints (shared-secret + user context headers).
 * This is the only HTTP boundary toward the AI service; tests replace it with a fake bean.
 */
@Component
public class HttpAiServiceClient implements AiServiceClient {

    private static final Logger log = LoggerFactory.getLogger(HttpAiServiceClient.class);

    private final RestClient restClient;
    private final String internalToken;

    public HttpAiServiceClient(RestClient.Builder builder, AppProperties props) {
        this.internalToken = props.getInternal().getToken();
        this.restClient = builder.baseUrl(props.getAiService().getBaseUrl()).build();
    }

    @Override
    public Map<String, Object> ingestDocument(UUID documentId, UUID userId) {
        return post("/internal/ingest/document/" + documentId, userId, Map.of());
    }

    @Override
    public Map<String, Object> ingestText(UUID userId, String title, String text, String kind, UUID refId) {
        Map<String, Object> body = new HashMap<>();
        body.put("title", title);
        body.put("text", text);
        body.put("kind", kind);
        if (refId != null) {
            body.put("ref_id", refId.toString());
        }
        return post("/internal/ingest/text", userId, body);
    }

    @Override
    public Map<String, Object> documentText(UUID documentId, UUID userId) {
        return get("/internal/ingest/documents/" + documentId + "/text", userId);
    }

    @Override
    public Map<String, Object> parseResumeText(String text, UUID userId) {
        return post("/internal/features/resume/parse", userId, Map.of("text", text));
    }

    @Override
    public Map<String, Object> analyzeJd(String rawText, UUID userId) {
        return post("/internal/features/jd/analyze", userId, Map.of("raw_text", rawText));
    }

    @Override
    public Map<String, Object> matchJob(UUID jobId, UUID resumeVersionId, UUID userId) {
        return post("/internal/features/match", userId, withOptionalRv("job_id", jobId, resumeVersionId));
    }

    @Override
    public Map<String, Object> tailorResume(UUID jobId, UUID resumeVersionId, UUID userId) {
        return post("/internal/features/tailor", userId, withOptionalRv("job_id", jobId, resumeVersionId));
    }

    @Override
    public Map<String, Object> coverLetter(UUID jobId, UUID resumeVersionId, String mode,
                                           String previous, String goal, UUID userId) {
        Map<String, Object> body = withOptionalRv("job_id", jobId, resumeVersionId);
        body.put("mode", mode == null || mode.isBlank() ? "generate" : mode);
        body.put("previous", previous == null ? "" : previous);
        body.put("goal", goal == null ? "" : goal);
        return post("/internal/features/cover-letter", userId, body);
    }

    @Override
    public Map<String, Object> jdSuggestions(UUID resumeVersionId, String jdRaw, UUID userId) {
        Map<String, Object> body = new HashMap<>();
        body.put("jd_raw", jdRaw);
        if (resumeVersionId != null) {
            body.put("resume_version_id", resumeVersionId.toString());
        }
        return post("/internal/features/jd/suggestions", userId, body);
    }

    @Override
    public Map<String, Object> interviewOpening(UUID sessionId, UUID userId) {
        return post("/internal/interview/opening", userId, Map.of("session_id", sessionId.toString()));
    }

    @Override
    public Map<String, Object> interviewAnswer(UUID sessionId, String answer, String question,
                                               List<Map<String, Object>> turns, UUID userId) {
        Map<String, Object> body = new HashMap<>();
        body.put("session_id", sessionId.toString());
        body.put("answer", answer);
        body.put("question", question == null ? "" : question);
        body.put("turns", turns);
        return post("/internal/interview/answer", userId, body);
    }

    @Override
    public Map<String, Object> interviewFinalize(UUID sessionId, List<Map<String, Object>> turns, UUID userId) {
        return post("/internal/interview/finalize", userId,
                Map.of("session_id", sessionId.toString(), "turns", turns));
    }

    @Override
    public Map<String, Object> copilotChatSync(String message, List<Map<String, Object>> history,
                                               UUID conversationId, Map<String, Object> context, UUID userId) {
        Map<String, Object> body = new HashMap<>();
        body.put("message", message);
        body.put("history", history == null ? List.of() : history);
        body.put("conversation_id", conversationId == null ? null : conversationId.toString());
        body.put("context", context == null ? Map.of() : context);
        return post("/internal/agents/chat/sync", userId, body);
    }

    private static Map<String, Object> withOptionalRv(String idKey, UUID id, UUID resumeVersionId) {
        Map<String, Object> body = new HashMap<>();
        body.put(idKey, id.toString());
        if (resumeVersionId != null) {
            body.put("resume_version_id", resumeVersionId.toString());
        }
        return body;
    }

    private Map<String, Object> post(String path, UUID userId, Map<String, Object> body) {
        return exchange(() -> restClient.post()
                .uri(path)
                .contentType(MediaType.APPLICATION_JSON)
                .header("X-Internal-Token", internalToken)
                .header("X-User-Id", userId.toString())
                .body(body)
                .retrieve()
                .body(Map.class));
    }

    private Map<String, Object> get(String path, UUID userId) {
        return exchange(() -> restClient.get()
                .uri(path)
                .header("X-Internal-Token", internalToken)
                .header("X-User-Id", userId.toString())
                .retrieve()
                .body(Map.class));
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> exchange(java.util.function.Supplier<Map> call) {
        try {
            Map raw = call.get();
            if (raw == null) {
                throw new ApiException(ApiErrorCode.AI_SERVICE_ERROR, "AI service returned empty body");
            }
            return (Map<String, Object>) raw;
        } catch (RestClientException e) {
            log.error("AI service call failed: {}", e.getMessage());
            throw new ApiException(ApiErrorCode.AI_SERVICE_ERROR, "AI service request failed");
        }
    }
}
