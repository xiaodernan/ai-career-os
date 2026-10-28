package com.careeros.report.service;

import com.careeros.ai.AiServiceClient;
import com.careeros.application.entity.Application;
import com.careeros.application.entity.ApplicationEvent;
import com.careeros.application.repository.ApplicationEventRepository;
import com.careeros.application.repository.ApplicationRepository;
import com.careeros.common.Paging;
import java.util.HashMap;
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

    /**
     * The stages the engine times a duration for: the status it saw, to the row key it
     * sends. Both spellings are the engine's — {@code analytics.py} derives its pipeline
     * from the same stage names and reads {@code <stage>_at} off the row, and a unit test
     * walks all three so neither side can drift into a key the other one never reads.
     */
    private static final Map<String, String> TIMED_STAGES = Map.of(
            "oa", "oa_at",
            "interview", "interview_at",
            "final_round", "final_round_at",
            "offer", "offer_at");

    /** The event kind that records a status transition, written by {@code applyStatusChange}. */
    private static final String STATUS_EVENT = "status";

    private final AiServiceClient aiService;
    private final ApplicationRepository applications;
    private final ApplicationEventRepository events;

    public AnalysisService(AiServiceClient aiService, ApplicationRepository applications,
            ApplicationEventRepository events) {
        this.aiService = aiService;
        this.applications = applications;
        this.events = events;
    }

    /**
     * The insight digest for the dashboard. The ai-service ranks stalled
     * applications, computes the stage mix, and derives headline rates; this
     * method supplies the rows and forwards the call, with the reader's
     * language ({@code locale}) when the page has one.
     */
    @Transactional(readOnly = true)
    public Map<String, Object> insightDigest(UUID userId, String locale) {
        return aiService.insightDigest(userId, applicationRows(userId), locale);
    }

    /**
     * The same digest with the staleness window spelled out, for the weekly letter (19.4): the
     * dashboard's window is a fortnight, but a letter about one week must call an application
     * quiet on the letter's own terms, or its stalled list would disagree with the week it
     * describes.
     */
    @Transactional(readOnly = true)
    public Map<String, Object> insightDigest(UUID userId, String locale, int staleDays) {
        return aiService.insightDigest(userId, applicationRows(userId), locale, staleDays);
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
        Map<UUID, Map<String, String>> reachedAt = firstTransitionTimes(userId);
        return applications.findByUserIdOrderByUpdatedAtDescIdAsc(
                        userId, Paging.first(MAX_APPLICATIONS)).stream()
                .map(a -> toInput(a, reachedAt.getOrDefault(a.getId(), Map.of())))
                .toList();
    }

    /**
     * When each application first reached each timed stage, read out of the status-transition
     * log. The engine's {@code timeInStage} needs a duration per stage, and a duration needs
     * the moment the stage was entered — which the application row itself cannot give, because
     * it stores only the current status. The events come oldest first, so the first transition
     * whose {@code to} is a timed stage wins, and a later re-entry cannot move the clock back.
     *
     * <p>Reading the log rather than the row is what makes the rejected application honest: a
     * candidate who reached an interview and was turned down afterwards carries
     * {@code interview_at}, so the engine can time that stage even though the funnel still
     * credits the row to {@code applied} (see {@code analytics.py}'s note on {@code rejected}).
     */
    private Map<UUID, Map<String, String>> firstTransitionTimes(UUID userId) {
        Map<UUID, Map<String, String>> reachedAt = new HashMap<>();
        for (ApplicationEvent event : events.findByUserIdAndKindOrderByCreatedAtAscIdAsc(
                userId, STATUS_EVENT)) {
            String key = TIMED_STAGES.get(String.valueOf(event.getPayload().get("to")));
            if (key == null || event.getCreatedAt() == null) {
                continue;
            }
            reachedAt.computeIfAbsent(event.getApplicationId(), id -> new HashMap<>())
                    .putIfAbsent(key, event.getCreatedAt().toString());
        }
        return reachedAt;
    }

    /**
     * One application as the engine reads it. The field names are the engine's
     * own (`applied_at`, `oa_at`, `last_seen`), and a field the row does not carry is
     * left out rather than sent as null: the engine skips an unparseable
     * timestamp instead of inventing a duration from one.
     */
    private static Map<String, Object> toInput(Application a, Map<String, String> reachedAt) {
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
        // Pipeline order, so the same row serialises the same way twice. Each key is
        // spelled at its own put because the row's shape is a contract another service
        // reads by name, and a contract a test can only check by reading this file.
        if (reachedAt.containsKey("oa_at")) {
            row.put("oa_at", reachedAt.get("oa_at"));
        }
        if (reachedAt.containsKey("interview_at")) {
            row.put("interview_at", reachedAt.get("interview_at"));
        }
        if (reachedAt.containsKey("final_round_at")) {
            row.put("final_round_at", reachedAt.get("final_round_at"));
        }
        if (reachedAt.containsKey("offer_at")) {
            row.put("offer_at", reachedAt.get("offer_at"));
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
