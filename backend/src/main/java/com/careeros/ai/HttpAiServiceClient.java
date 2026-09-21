package com.careeros.ai;

import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.config.AppProperties;
import java.util.Map;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

/**
 * Typed wrapper around the ai-service /internal/* endpoints (shared-secret + user context headers).
 * Add one method per AI capability as domain modules land; keep this the only HTTP boundary.
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
    public IngestResult ingestDocument(UUID documentId, UUID userId) {
        return post("/internal/documents/" + documentId + "/ingest", userId, IngestResult.class);
    }

    @Override
    public ResumeParseResult parseResume(UUID resumeId, UUID userId) {
        return post("/internal/resumes/" + resumeId + "/parse", userId, ResumeParseResult.class);
    }

    private <T> T post(String path, UUID userId, Class<T> responseType) {
        try {
            return restClient.post()
                    .uri(path)
                    .contentType(MediaType.APPLICATION_JSON)
                    .header(HttpHeaders.AUTHORIZATION, "Bearer " + internalToken)
                    .header("X-Internal-Token", internalToken)
                    .header("X-User-Id", userId.toString())
                    .body(Map.of())
                    .retrieve()
                    .body(responseType);
        } catch (RestClientException e) {
            log.error("AI service call failed: {} {}", path, e.getMessage());
            throw new ApiException(ApiErrorCode.AI_SERVICE_ERROR, "AI service request failed");
        }
    }
}
