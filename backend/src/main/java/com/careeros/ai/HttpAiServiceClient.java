package com.careeros.ai;

import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.common.EnvelopeJson;
import com.careeros.common.RequestIdFilter;
import com.careeros.config.AppProperties;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
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

    /** How long an upstream sentence may be before the toast cuts it. */
    private static final int MAX_UPSTREAM_DETAIL = 300;

    /**
     * How long the health probe waits, connect and answer together. Shorter than any
     * user-facing call's budget on purpose: the health line answers in bounded time even
     * when the AI half is hung, and "nothing answered within two seconds" is the answer.
     */
    private static final Duration HEALTH_TIMEOUT = Duration.ofSeconds(2);

    private final RestClient restClient;
    private final String internalToken;
    private final String baseUrl;
    private final HttpClient healthClient;

    public HttpAiServiceClient(RestClient.Builder builder, AppProperties props) {
        this.internalToken = props.getInternal().getToken();
        this.baseUrl = props.getAiService().getBaseUrl().replaceAll("/+$", "");
        this.healthClient = HttpClient.newBuilder()
                .version(HttpClient.Version.HTTP_1_1)
                .connectTimeout(HEALTH_TIMEOUT)
                .build();
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
                // The ai-service logs the same id, so one grep follows a turn across both
                // services. Calls made outside a request (the nightly sweep) have none and
                // send none; the ai-service mints its own and logs that.
                .requestInterceptor((request, body, execution) -> {
                    String requestId = RequestIdFilter.currentId();
                    if (requestId != null) {
                        request.getHeaders().set(RequestIdFilter.HEADER, requestId);
                    }
                    return execution.execute(request, body);
                })
                .build();
    }

    /**
     * The ai-service's own public health route, asked over its own small client. No internal
     * token and no user id: the route does not need them, and the probe should not carry a
     * secret to a door that never asks for one. Anything that is not a 2xx -- a refusal, a
     * timeout, a socket that never opened -- is false; a failed probe is a report, not an
     * exception.
     */
    @Override
    public boolean healthy() {
        try {
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(baseUrl + "/health"))
                    .timeout(HEALTH_TIMEOUT)
                    .GET()
                    .build();
            return healthClient.send(request, HttpResponse.BodyHandlers.discarding()).statusCode() / 100 == 2;
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return false;
        } catch (Exception e) {
            return false;
        }
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
    public Map<String, Object> voiceState(UUID userId) {
        return get("/internal/voice/status", userId);
    }

    @Override
    public Map<String, Object> transcribeAnswer(UUID userId, String audio, String mime, String locale) {
        Map<String, Object> body = new HashMap<>();
        body.put("audio", audio);
        body.put("mime", mime == null || mime.isBlank() ? "audio/webm" : mime);
        if (locale != null && !locale.isBlank()) {
            body.put("locale", locale);
        }
        return post("/internal/voice/transcribe", userId, body);
    }

    @Override
    public Map<String, Object> speakQuestion(UUID userId, String text, String locale) {
        Map<String, Object> body = new HashMap<>();
        body.put("text", text);
        if (locale != null && !locale.isBlank()) {
            body.put("locale", locale);
        }
        return post("/internal/voice/speak", userId, body);
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
            throw new ApiException(ApiErrorCode.AI_SERVICE_UNAVAILABLE, "AI service request failed");
        }
    }

    @Override
    @SuppressWarnings("unchecked")
    public List<Map<String, Object>> followUps(UUID userId) {
        Object items = post("/internal/features/follow-ups", userId, Map.of()).get("items");
        return items instanceof List<?> list ? (List<Map<String, Object>>) list : List.of();
    }

    @Override
    public Map<String, Object> insightDigest(UUID userId, List<Map<String, Object>> applications,
                                             String locale) {
        // The engine's own default window, spelled out so both entry points build one body.
        return insightDigest(userId, applications, locale, 14);
    }

    @Override
    public Map<String, Object> insightDigest(UUID userId, List<Map<String, Object>> applications,
                                             String locale, int staleDays) {
        Map<String, Object> body = new HashMap<>();
        body.put("applications", applications);
        body.put("stale_days", staleDays);
        if (locale != null && !locale.isBlank()) {
            body.put("locale", locale);
        }
        return post("/internal/features/insight-digest", userId, body);
    }

    @Override
    public Map<String, Object> exportBundle(UUID userId, boolean anonymized,
                                           Map<String, Object> sections) {
        Map<String, Object> body = new HashMap<>();
        body.put("anonymized", anonymized);
        if (sections != null && !sections.isEmpty()) {
            body.put("sections", sections);
        }
        return post("/internal/features/export-bundle", userId, body);
    }

    @Override
    public Map<String, Object> importPlan(UUID userId, Map<String, Object> bundle, Map<String, Object> existing) {
        Map<String, Object> body = new HashMap<>();
        body.put("bundle", bundle);
        if (existing != null) {
            body.put("existing", existing);
        }
        return post("/internal/features/import-plan", userId, body);
    }

    @Override
    public Map<String, Object> redactBundle(UUID userId, Map<String, Object> bundle, List<String> drop) {
        Map<String, Object> body = new HashMap<>();
        body.put("bundle", bundle);
        if (drop != null) {
            body.put("drop", drop);
        }
        return post("/internal/features/redact-bundle", userId, body);
    }

    @Override
    public Map<String, Object> renderBundle(UUID userId, Map<String, Object> bundle, String format) {
        return renderBundle(userId, bundle, format, null);
    }

    @Override
    public Map<String, Object> renderBundle(UUID userId, Map<String, Object> bundle, String format,
                                            String locale) {
        Map<String, Object> body = new HashMap<>();
        body.put("bundle", bundle);
        body.put("format", format == null || format.isBlank() ? "html" : format);
        if (locale != null && !locale.isBlank()) {
            body.put("locale", locale);
        }
        return post("/internal/features/render-bundle", userId, body);
    }

    @Override
    public Map<String, Object> renderResume(UUID userId, Map<String, Object> resume, String text,
                                            String title, String subtitle, String locale) {
        Map<String, Object> body = new HashMap<>();
        body.put("resume", resume == null ? Map.of() : resume);
        if (text != null && !text.isBlank()) {
            body.put("text", text);
        }
        if (title != null && !title.isBlank()) {
            body.put("title", title);
        }
        if (subtitle != null && !subtitle.isBlank()) {
            body.put("subtitle", subtitle);
        }
        if (locale != null && !locale.isBlank()) {
            body.put("locale", locale);
        }
        return post("/internal/features/render-resume", userId, body);
    }

    @Override
    public Map<String, Object> parseFeed(String feed, String source, UUID userId) {
        // The feed's shape is detected by the engine, so an RSS 2.0 / Atom
        // XML feed and a board-API JSON payload both come through this one
        // route -- which is what the ingestion page promises.
        //
        // A `HashMap` and not `Map.of`, because `Map.of` rejects a null value
        // and `source` is a caller's optional field: a client that omits it
        // used to reach `Map.of` with a null and get a 500 out of the
        // bridge, which is our bug and not the caller's.
        Map<String, Object> body = new HashMap<>();
        body.put("payload", feed);
        body.put("source", source);
        return post("/internal/features/parse-feed", userId, body);
    }

    @Override
    public Map<String, Object> dedupeJobs(List<Map<String, Object>> postings, UUID userId) {
        return post("/internal/features/dedupe-jobs", userId, Map.of("postings", postings));
    }

    @Override
    public Map<String, Object> freshnessSweep(List<Map<String, Object>> postings, int maxAgeDays,
                                               int staleSeenDays, UUID userId) {
        return post("/internal/features/freshness-sweep", userId,
                Map.of("postings", postings, "max_age_days", maxAgeDays, "stale_seen_days", staleSeenDays));
    }

    @Override
    public Map<String, Object> planIngest(String feed, String source, List<Map<String, Object>> existing,
                                           int maxAgeDays, int staleSeenDays, UUID userId, String company) {
        Map<String, Object> body = new HashMap<>();
        body.put("feed", feed);
        body.put("source", source);
        if (existing != null) {
            body.put("existing", existing);
        }
        if (company != null && !company.isBlank()) {
            body.put("company", company);
        }
        body.put("max_age_days", maxAgeDays);
        body.put("stale_seen_days", staleSeenDays);
        return post("/internal/features/plan-ingest", userId, body);
    }

    @Override
    public Map<String, Object> healthReport(UUID userId, List<Map<String, Object>> runs) {
        return post("/internal/features/health-report", userId, Map.of("runs", runs));
    }

    @Override
    public Map<String, Object> salaryBenchmark(UUID userId, com.careeros.ai.dto.OfferDtos.SalaryRequest request) {
        Map<String, Object> body = new HashMap<>();
        body.put("role", request.role());
        if (request.location() != null) body.put("location", request.location());
        if (request.seniority() != null) body.put("seniority", request.seniority());
        if (request.targetSalary() != null) body.put("target_salary", request.targetSalary());
        if (request.currency() != null) body.put("currency", request.currency());
        return post("/internal/features/salary-benchmark", userId, body);
    }

    @Override
    public Map<String, Object> negotiate(UUID userId, com.careeros.ai.dto.OfferDtos.NegotiationRequest request) {
        Map<String, Object> body = new HashMap<>();
        body.put("role", request.role());
        if (request.location() != null) body.put("location", request.location());
        if (request.seniority() != null) body.put("seniority", request.seniority());
        if (request.currency() != null) body.put("currency", request.currency());
        body.put("offer_base", request.offerBase());
        if (request.matchScore() != null) body.put("match_score", request.matchScore());
        return post("/internal/features/negotiate", userId, body);
    }

    @Override
    public Map<String, Object> compareOffers(UUID userId, com.careeros.ai.dto.OfferDtos.CompareOffersRequest request) {
        Map<String, Object> body = new HashMap<>();
        body.put("role", request.role());
        if (request.location() != null) body.put("location", request.location());
        if (request.seniority() != null) body.put("seniority", request.seniority());
        if (request.currency() != null) body.put("currency", request.currency());
        if (request.matchScore() != null) body.put("match_score", request.matchScore());
        List<Map<String, Object>> offers = request.offers().stream()
                .map(HttpAiServiceClient::offerBody)
                .toList();
        body.put("offers", offers);
        return post("/internal/features/compare-offers", userId, body);
    }

    @Override
    public Map<String, Object> counterOffer(UUID userId, com.careeros.ai.dto.OfferDtos.CounterOfferRequest request) {
        Map<String, Object> body = new HashMap<>();
        body.put("role", request.role());
        if (request.location() != null) body.put("location", request.location());
        if (request.seniority() != null) body.put("seniority", request.seniority());
        if (request.currency() != null) body.put("currency", request.currency());
        body.put("offer_base", request.offerBase());
        if (request.matchScore() != null) body.put("match_score", request.matchScore());
        return post("/internal/features/counter-offer", userId, body);
    }

    /** One offer, in the engine's own field names. The equity grant is nested. */
    private static Map<String, Object> offerBody(com.careeros.ai.dto.OfferDtos.OfferItem offer) {
        Map<String, Object> body = new HashMap<>();
        body.put("label", offer.label());
        body.put("base", offer.base());
        body.put("bonus", offer.bonus());
        if (offer.equity() != null) {
            Map<String, Object> equity = new HashMap<>();
            equity.put("shares", offer.equity().shares());
            equity.put("strike_price", offer.equity().strikePrice());
            equity.put("current_price", offer.equity().currentPrice());
            if (offer.equity().vestYears() != null) equity.put("vest_years", offer.equity().vestYears());
            body.put("equity", equity);
        }
        return body;
    }

    @Override
    public Map<String, Object> gapAnalysis(UUID userId, com.careeros.ai.dto.GrowthEngineRequest request) {
        Map<String, Object> body = new HashMap<>();
        body.put("target_role", request.targetRole());
        if (request.seniority() != null) body.put("seniority", request.seniority());
        if (request.resumeVersionId() != null) body.put("resume_version_id", request.resumeVersionId());
        return post("/internal/features/gap-analysis", userId, body);
    }

    @Override
    public Map<String, Object> readiness(UUID userId, com.careeros.ai.dto.GrowthEngineRequest request) {
        Map<String, Object> body = new HashMap<>();
        body.put("target_role", request.targetRole());
        if (request.seniority() != null) body.put("seniority", request.seniority());
        if (request.resumeVersionId() != null) body.put("resume_version_id", request.resumeVersionId());
        if (request.location() != null) body.put("location", request.location());
        if (request.currency() != null) body.put("currency", request.currency());
        if (request.targetSalary() != null) body.put("target_salary", request.targetSalary());
        return post("/internal/features/readiness", userId, body);
    }

    @Override
    public Map<String, Object> learningPlan(UUID userId, com.careeros.ai.dto.GrowthEngineRequest request) {
        Map<String, Object> body = new HashMap<>();
        body.put("target_role", request.targetRole());
        if (request.seniority() != null) body.put("seniority", request.seniority());
        if (request.resumeVersionId() != null) body.put("resume_version_id", request.resumeVersionId());
        return post("/internal/features/learning-plan", userId, body);
    }

    @Override
    public Map<String, Object> skillDemand(UUID userId, com.careeros.ai.dto.GrowthEngineRequest request) {
        // The demand engine asks what the market wants for a role family, so it
        // names the role as `role` rather than `target_role`, and it reads no
        // seniority band of its own.
        Map<String, Object> body = new HashMap<>();
        body.put("role", request.targetRole());
        if (request.location() != null) body.put("location", request.location());
        if (request.top() != null) body.put("top", request.top());
        return post("/internal/features/skill-demand", userId, body);
    }

    @Override
    public Map<String, Object> learningPriority(UUID userId, com.careeros.ai.dto.GrowthEngineRequest request) {
        Map<String, Object> body = new HashMap<>();
        body.put("target_role", request.targetRole());
        if (request.seniority() != null) body.put("seniority", request.seniority());
        if (request.resumeVersionId() != null) body.put("resume_version_id", request.resumeVersionId());
        return post("/internal/features/learning-priority", userId, body);
    }

    @Override
    public Map<String, Object> progression(UUID userId, com.careeros.ai.dto.GrowthEngineRequest request) {
        // The progression engine names the role it is planning toward differently:
        // it is the dream role, not the one the candidate holds.
        Map<String, Object> body = new HashMap<>();
        body.put("aspirational_role", request.targetRole());
        if (request.seniority() != null) body.put("seniority", request.seniority());
        if (request.resumeVersionId() != null) body.put("resume_version_id", request.resumeVersionId());
        return post("/internal/features/progression", userId, body);
    }

    @Override
    public Map<String, Object> interviewPrep(UUID userId, com.careeros.ai.dto.GrowthEngineRequest request) {
        Map<String, Object> body = new HashMap<>();
        body.put("target_role", request.targetRole());
        if (request.seniority() != null) body.put("seniority", request.seniority());
        if (request.resumeVersionId() != null) body.put("resume_version_id", request.resumeVersionId());
        return post("/internal/features/interview-prep", userId, body);
    }

    @Override
    public Map<String, Object> storyBank(UUID userId, com.careeros.ai.dto.ProfileEngineRequest request) {
        Map<String, Object> body = new HashMap<>();
        if (request.resumeVersionId() != null) body.put("resume_version_id", request.resumeVersionId());
        return post("/internal/features/story-bank", userId, body);
    }

    @Override
    public Map<String, Object> roleSuggestions(UUID userId, com.careeros.ai.dto.ProfileEngineRequest request) {
        Map<String, Object> body = new HashMap<>();
        if (request.resumeVersionId() != null) body.put("resume_version_id", request.resumeVersionId());
        if (request.top() != null) body.put("top", request.top());
        return post("/internal/features/role-suggestions", userId, body);
    }

    @Override
    public Map<String, Object> progress(UUID userId, com.careeros.ai.dto.ProgressRequest request) {
        Map<String, Object> body = new HashMap<>();
        if (request.targetRole() != null) body.put("target_role", request.targetRole());
        if (request.seniority() != null) body.put("seniority", request.seniority());
        if (request.resumeVersionId() != null) body.put("resume_version_id", request.resumeVersionId());
        if (request.previous() != null) body.put("previous", request.previous());
        return post("/internal/features/progress", userId, body);
    }

    @Override
    public Map<String, Object> outreach(UUID userId, com.careeros.ai.dto.OutreachRequest request) {
        Map<String, Object> body = new HashMap<>();
        body.put("name", request.name());
        body.put("role", request.role() == null ? "" : request.role());
        body.put("company", request.company() == null ? "" : request.company());
        body.put("purpose", request.purpose() == null ? "referral" : request.purpose());
        body.put("context", request.context() == null ? "" : request.context());
        if (request.resumeVersionId() != null) body.put("resume_version_id", request.resumeVersionId());
        return post("/internal/features/outreach", userId, body);
    }

    @Override
    public Map<String, Object> classifyReply(UUID userId, String text) {
        return post("/internal/features/classify-reply", userId, Map.of("text", text));
    }

    @Override
    public Map<String, Object> pipelineFunnel(UUID userId, List<Map<String, Object>> applications) {
        return post("/internal/features/pipeline-funnel", userId, Map.of("applications", applications));
    }

    @Override
    public Map<String, Object> responseRate(UUID userId, List<Map<String, Object>> applications) {
        return post("/internal/features/response-rate", userId, Map.of("applications", applications));
    }

    @Override
    public Map<String, Object> companyBrief(UUID userId, com.careeros.ai.dto.CompanyBriefRequest request) {
        Map<String, Object> body = new HashMap<>();
        body.put("company", request.company());
        if (request.top() != null) body.put("top", request.top());
        return post("/internal/features/company-brief", userId, body);
    }

    @Override
    public Map<String, Object> importMemories(UUID userId, List<Map<String, Object>> memories) {
        return post("/internal/memories/import", userId, Map.of("memories", memories));
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
                throw new ApiException(ApiErrorCode.AI_SERVICE_EMPTY_RESPONSE, "AI service returned empty body");
            }
            return (Map<String, Object>) raw;
        } catch (RestClientResponseException e) {
            throw translateStatus(e);
        } catch (RestClientException e) {
            log.error("AI service call failed: {}", e.getMessage());
            throw new ApiException(ApiErrorCode.AI_SERVICE_UNAVAILABLE, "AI service request failed");
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
     *
     * A 400 also carries the upstream's own sentence, because a refused file is the
     * caller's to fix: "invalid bundle: missing data section: knowledge" tells a reader
     * which part of their file the product did not understand, and "AI service rejected
     * the request" names the wrong party and tells them nothing. The sentence arrives
     * two ways now: as a bare string (the legacy shape) and inside the ai-service's
     * typed refusals, which answer {"detail": {"code": ..., "message": ...}} so the
     * upstream's own vocabulary survives the crossing. Both are read; the code stays
     * upstream until this service learns to map it.
     */
    private static ApiException translateStatus(RestClientResponseException e) {
        HttpStatus status = HttpStatus.resolve(e.getStatusCode().value());
        if (status == HttpStatus.NOT_FOUND) {
            return new ApiException(ApiErrorCode.AI_SERVICE_NOT_FOUND, "Resource not found");
        }
        if (status == HttpStatus.BAD_REQUEST || status == HttpStatus.UNPROCESSABLE_ENTITY) {
            String detail = upstreamDetail(e);
            return new ApiException(ApiErrorCode.AI_SERVICE_BAD_REQUEST,
                    detail != null ? detail : "AI service rejected the request");
        }
        if (status == HttpStatus.CONFLICT) {
            // The upstream has the record and it is not ready yet -- the
            // document is still being read. A 502 would say the assistant
            // failed, which is a different thing and a wrong one.
            return new ApiException(ApiErrorCode.AI_SERVICE_CONFLICT, "AI service is not ready yet");
        }
        log.error("AI service call failed with status {}", status);
        return new ApiException(ApiErrorCode.AI_SERVICE_UNAVAILABLE, "AI service request failed");
    }

    /** The upstream's own sentence, when it sent one that is a sentence. */
    private static String upstreamDetail(RestClientResponseException e) {
        try {
            String body = e.getResponseBodyAsString();
            if (body == null || body.isBlank()) {
                return null;
            }
            @SuppressWarnings("unchecked")
            Map<String, Object> parsed = EnvelopeJson.MAPPER.readValue(body, Map.class);
            Object detail = parsed.get("detail");
            String sentence = null;
            if (detail instanceof String text && !text.isBlank()) {
                sentence = text;
            } else if (detail instanceof Map<?, ?> refusal) {
                // The ai-service's typed refusals answer with a structured
                // detail: {"code": "INGEST_FEED_EMPTY", "message": "feed is
                // empty"}. The sentence is still the reader's; the code is
                // the upstream's own vocabulary, which this service does not
                // speak yet.
                Object message = refusal.get("message");
                if (message instanceof String text && !text.isBlank()) {
                    sentence = text;
                }
            }
            if (sentence == null) {
                return null;
            }
            return clip(sentence);
        } catch (Exception ignored) {
            // A body we cannot read is a body we have no sentence in.
            return null;
        }
    }

    /** A toast is not a document: a long sentence is cut rather than scrolled. */
    private static String clip(String sentence) {
        return sentence.length() > MAX_UPSTREAM_DETAIL
                ? sentence.substring(0, MAX_UPSTREAM_DETAIL) + "…"
                : sentence;
    }
}
