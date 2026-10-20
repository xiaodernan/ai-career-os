package com.careeros.report.service;

import com.careeros.ai.AiServiceClient;
import com.careeros.application.entity.Application;
import com.careeros.application.repository.ApplicationRepository;
import com.careeros.common.Paging;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * The weekly insight digest (15.3): stalled applications, live stage mix, and
 * headline rates, composed by the ai-service's analytics engine.
 *
 * <p>The engine is a pure function over the caller's application rows, so the
 * backend's job is to hand it those rows. The engine never reads the database
 * itself — the backend owns the domain writes, and a second reader of the same
 * table is a second answer to the same question.
 */
@Service
public class AnalysisService {

    /** The digest walks the caller's whole history; a cap keeps the request bounded. */
    private static final int MAX_APPLICATIONS = 500;

    private final AiServiceClient aiService;
    private final ApplicationRepository applications;

    public AnalysisService(AiServiceClient aiService, ApplicationRepository applications) {
        this.aiService = aiService;
        this.applications = applications;
    }

    /**
     * The insight digest for the dashboard. The ai-service ranks stalled
     * applications, computes the stage mix, and derives headline rates; this
     * method supplies the rows and forwards the call.
     */
    @Transactional(readOnly = true)
    public Map<String, Object> insightDigest(UUID userId) {
        return aiService.insightDigest(userId, applicationRows(userId));
    }

    /**
     * 15.1 — the pipeline funnel: how many applications reached each stage, and
     * where the leak is. The same rows the digest reads, one lens on them.
     */
    @Transactional(readOnly = true)
    public Map<String, Object> pipelineFunnel(UUID userId) {
        return aiService.pipelineFunnel(userId, applicationRows(userId));
    }

    /**
     * 15.2 — the reply / interview / offer rates and the per-stage durations.
     * A rejection counts as a response: a no is still an answer.
     */
    @Transactional(readOnly = true)
    public Map<String, Object> responseRate(UUID userId) {
        return aiService.responseRate(userId, applicationRows(userId));
    }

    /** The caller's application rows, in the engine's own field names. */
    private List<Map<String, Object>> applicationRows(UUID userId) {
        return applications.findByUserIdOrderByUpdatedAtDescIdAsc(
                        userId, Paging.first(MAX_APPLICATIONS)).stream()
                .map(AnalysisService::toInput)
                .toList();
    }

    /**
     * One application as the engine reads it. The field names are the engine's
     * own (`applied_at`, `created_at`), and a field the row does not carry is
     * left out rather than sent as null: the engine skips an unparseable
     * timestamp instead of inventing a duration from one.
     */
    private static Map<String, Object> toInput(Application a) {
        Map<String, Object> row = new LinkedHashMap<>();
        // The id is the engine's key for the row, so it is never absent — but a
        // row the database has not stamped yet must not take the whole digest
        // down with a null dereference either.
        row.put("id", a.getId() == null ? "" : a.getId().toString());
        row.put("status", a.getStatus());
        row.put("title", a.getTitle());
        if (a.getCompanyName() != null) {
            row.put("company", a.getCompanyName());
        }
        if (a.getAppliedAt() != null) {
            row.put("applied_at", a.getAppliedAt().toString());
        }
        if (a.getCreatedAt() != null) {
            row.put("created_at", a.getCreatedAt().toString());
        }
        if (a.getUpdatedAt() != null) {
            row.put("last_seen", a.getUpdatedAt().toString());
        }
        return row;
    }
}
