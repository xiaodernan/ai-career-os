package com.careeros.ai;

import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.config.AppProperties;
import java.net.http.HttpClient;
import java.time.Duration;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestClientResponseException;

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
        // JDK HttpClient defaults to HTTP/2 and probes with an h2c upgrade; uvicorn rejects the
        // upgrade and loses the request body (FastAPI then 422s with body=null). Force HTTP/1.1.
        HttpClient httpClient = HttpClient.newBuilder()
                .version(HttpClient.Version.HTTP_1_1)
                .connectTimeout(Duration.ofSeconds(5))
                .build();
        JdkClientHttpRequestFactory factory = new JdkClientHttpRequestFactory(httpClient);
        factory.setReadTimeout(Duration.ofSeconds(180));
        this.restClient = builder.baseUrl(props.getAiService().getBaseUrl())
                .requestFactory(factory)
                .build();
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
                                           String previous, String goal, String tone,
                                           String length, UUID userId) {
        Map<String, Object> body = withOptionalRv("job_id", jobId, resumeVersionId);
        body.put("mode", mode == null || mode.isBlank() ? "generate" : mode);
        body.put("previous", previous == null ? "" : previous);
        body.put("goal", goal == null ? "" : goal);
        body.put("tone", tone == null ? "" : tone);
        body.put("length", length == null ? "" : length);
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
        return post("/internal/agents/chat/sync", userId, chatBody(message, history, conversationId, context));
    }

    @Override
    public Map<String, Object> copilotChatStart(String message, List<Map<String, Object>> history,
                                                UUID conversationId, Map<String, Object> context, UUID userId) {
        return post("/internal/agents/chat", userId, chatBody(message, history, conversationId, context));
    }

    @Override
    public Map<String, Object> embedQuery(String text, UUID userId) {
        return post("/internal/rag/embeddings", userId, Map.of("text", text));
    }

    @Override
    public Map<String, Object> growthReport(com.careeros.ai.dto.GrowthReportRequest request,
                                            UUID userId) {
        Map<String, Object> body = new HashMap<>();
        body.put("target_role", request.targetRole());
        if (request.seniority() != null) body.put("seniority", request.seniority());
        if (request.resumeVersionId() != null) {
            body.put("resume_version_id", request.resumeVersionId().toString());
        }
        if (request.location() != null) body.put("location", request.location());
        if (request.currency() != null) body.put("currency", request.currency());
        if (request.targetSalary() != null) body.put("target_salary", request.targetSalary());
        if (request.previous() != null) body.put("previous", request.previous());
        return post("/internal/features/growth-report", userId, body);
    }

    @Override
    @SuppressWarnings("unchecked")
    public List<Map<String, Object>> listMemories(List<String> kinds, UUID userId) {
        String path = "/internal/memories"
                + (kinds == null || kinds.isEmpty() ? "" : "?kinds=" + String.join(",", kinds));
        Object items = get(path, userId).get("items");
        // A missing or wrong-typed `items` is an empty list, not a ClassCastException: the
        // page it feeds says "no memories" either way, which is the honest answer.
        return items instanceof List<?> list ? (List<Map<String, Object>>) list : List.of();
    }

    @Override
    public Map<String, Object> patchMemory(UUID memoryId, String content, Double importance,
                                           UUID userId) {
        Map<String, Object> body = new HashMap<>();
        if (content != null) {
            body.put("content", content);
        }
        if (importance != null) {
            body.put("importance", importance);
        }
        return patch("/internal/memories/" + memoryId, userId, body);
    }

    @Override
    public void deleteMemory(UUID memoryId, UUID userId) {
        // 204, so the shared `exchange` helper's Map return does not apply. The one call that
        // has nothing to read back: "gone" is the body. Its 404 ("not yours" / "not there")
        // still has to travel the same translation `exchange` applies, so a foreign id answers
        // 404 to the browser instead of the 502 this method's own catch used to flatten it to.
        try {
            restClient.delete()
                    .uri("/internal/memories/" + memoryId)
                    .header("X-Internal-Token", internalToken)
                    .header("X-User-Id", userId.toString())
                    .retrieve()
                    .toBodilessEntity();
        } catch (RestClientResponseException e) {
            throw translateStatus(e);
        } catch (RestClientException e) {
            log.error("AI service call failed: {}", e.getMessage());
            throw new ApiException(ApiErrorCode.AI_SERVICE_ERROR, "AI service request failed");
        }
    }

    /** One request shape for both chat routes, so the two cannot drift on what the turn is given. */
    private static Map<String, Object> chatBody(String message, List<Map<String, Object>> history,
                                                UUID conversationId, Map<String, Object> context) {
        Map<String, Object> body = new HashMap<>();
        body.put("message", message);
        body.put("history", history == null ? List.of() : history);
        body.put("conversation_id", conversationId == null ? null : conversationId.toString());
        body.put("context", context == null ? Map.of() : context);
        return body;
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

    /**
     * PATCH, the verb the two update endpoints use. Kept beside `post` for the same reason it
     * reads the same way as it: one verb per helper, so the route is the argument and the
     * request's shape is written once.
     */
    private Map<String, Object> patch(String path, UUID userId, Map<String, Object> body) {
        return exchange(() -> restClient.patch()
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
        } catch (RestClientResponseException e) {
            throw translateStatus(e);
        } catch (RestClientException e) {
            log.error("AI service call failed: {}", e.getMessage());
            throw new ApiException(ApiErrorCode.AI_SERVICE_ERROR, "AI service request failed");
        }
    }

    /**
     * The one place the ai-service's own status codes become this service's error codes.
     * {@code retrieve()} throws on any 4xx/5xx response, and every upstream route that
     * answers 404 ("not yours" and "not there" are the same answer in its WHERE clause)
     * or 400 (blank content, out-of-range weight) was being flattened into a 502 by the
     * catch-all below — the MemoryController's documented "answers 404 rather than 403"
     * was unreachable from HTTP. Connection failures and timeouts stay 502: nothing
     * upstream answered, so nothing upstream can be quoted.
     */
    private static ApiException translateStatus(RestClientResponseException e) {
        HttpStatus status = HttpStatus.resolve(e.getStatusCode().value());
        if (status == HttpStatus.NOT_FOUND) {
            return new ApiException(ApiErrorCode.NOT_FOUND, "Resource not found");
        }
        if (status == HttpStatus.BAD_REQUEST || status == HttpStatus.UNPROCESSABLE_ENTITY) {
            return new ApiException(ApiErrorCode.BAD_REQUEST, "AI service rejected the request");
        }
        log.error("AI service call failed with status {}", status);
        return new ApiException(ApiErrorCode.AI_SERVICE_ERROR, "AI service request failed");
    }
}
