package com.careeros.ai.service;

import com.careeros.ai.AiServiceClient;
import com.careeros.ai.dto.GapNoteRequest;
import com.careeros.ai.dto.GrowthEngineRequest;
import com.careeros.ai.dto.ProfileEngineRequest;
import com.careeros.ai.dto.ProgressRequest;
import java.util.Map;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * The granular growth engines (Epics 10.1-10.13), each as its own route.
 *
 * <p>The 10.2 aggregate composes the same engines for the growth page in one
 * call. These routes are the same engines asked one at a time, so a caller that
 * only wants the gap analysis does not have to run the whole report to get it.
 *
 * <p>Every engine is a deterministic read of the candidate's own resume and the
 * seeded corpus, so the bridge forwards the request and owns none of the logic.
 */
@Service
public class GrowthEngineService {

    private final AiServiceClient aiService;
    private final JdbcTemplate jdbc;

    public GrowthEngineService(AiServiceClient aiService, JdbcTemplate jdbc) {
        this.aiService = aiService;
        this.jdbc = jdbc;
    }

    /** 10.1 — the distance between the profile and the target role. */
    @Transactional(readOnly = true)
    public Map<String, Object> gapAnalysis(UUID userId, GrowthEngineRequest request) {
        return aiService.gapAnalysis(userId, request);
    }

    /** The latest resume's plaintext, compacted to one line — the evidence half the gap note used to lack. */
    private String currentPlaintextSnippet(UUID userId) {
        try {
            String sql = """
                SELECT v.plaintext
                  FROM resumes r
                  JOIN resume_versions v ON v.resume_id = r.id
                 WHERE r.user_id = ?
                 ORDER BY v.created_at DESC
                 LIMIT 1
            """;
            String text = jdbc.query(sql, new Object[]{userId}, rs -> rs.next() ? rs.getString(1) : null);
            if (text == null || text.isBlank()) {
                return null;
            }
            String compact = text.replaceAll("\\s+", " ").trim();
            return compact.length() <= 2400 ? compact : compact.substring(0, 2400);
        } catch (Exception ignored) {
            return null;
        }
    }

    /**
     * Epic 329 — the gap analyst's voice about the gap analysis. Runs the same engine
     * the caller could reach at /gap-analysis, then forwards the payload to the ai-service for
     * the one grounded paragraph. The backend owns the engine seam; the caller owns only
     * the locale toggle. Returns `{gap, note?}` — `note` is null when the editor could not
     * keep a grounded one. A coat of plausibility is never an acceptable answer.
     *
     * The payload now also carries up to 2400 chars of the reader's latest resume so the
     * editor can ground the note in their actual evidence, not just the coverage arithmetic —
     * the editor is still barred from inventing a fact, and the wire digits rule still holds.
     */
    @Transactional(readOnly = true)
    public Map<String, Object> gapNote(UUID userId, GapNoteRequest request) {
        GrowthEngineRequest engine = new GrowthEngineRequest(
                request.targetRole(), request.seniority(), null, null, null, null, null);
        Map<String, Object> payload = new java.util.HashMap<>(aiService.gapAnalysis(userId, engine));
        String evidence = currentPlaintextSnippet(userId);
        if (evidence != null) {
            payload.put("evidence", evidence);
        }
        Map<String, Object> answered = aiService.gapNote(userId, payload, request.locale());
        Object note = answered == null ? null : answered.get("note");
        if (note != null) {
            payload.put("note", note);
        }
        return payload;
    }

    /** 10.7 — target-role readiness, as one verdict. */
    @Transactional(readOnly = true)
    public Map<String, Object> readiness(UUID userId, GrowthEngineRequest request) {
        return aiService.readiness(userId, request);
    }

    /** 10.5 — the phased learning plan that closes the gaps. */
    @Transactional(readOnly = true)
    public Map<String, Object> learningPlan(UUID userId, GrowthEngineRequest request) {
        return aiService.learningPlan(userId, request);
    }

    /** 10.9 — which skills the market asks for, counted from the corpus. */
    @Transactional(readOnly = true)
    public Map<String, Object> skillDemand(UUID userId, GrowthEngineRequest request) {
        return aiService.skillDemand(userId, request);
    }

    /** 10.12 — the gaps ranked by importance and by market pull. */
    @Transactional(readOnly = true)
    public Map<String, Object> learningPriority(UUID userId, GrowthEngineRequest request) {
        return aiService.learningPriority(userId, request);
    }

    /** 10.11 — the stepping-stone roles toward a dream role. */
    @Transactional(readOnly = true)
    public Map<String, Object> progression(UUID userId, GrowthEngineRequest request) {
        return aiService.progression(userId, request);
    }

    /** 10.13 — the pre-interview checklist. */
    @Transactional(readOnly = true)
    public Map<String, Object> interviewPrep(UUID userId, GrowthEngineRequest request) {
        return aiService.interviewPrep(userId, request);
    }

    /** 6.5 — the STAR story bank, drawn from the profile's own evidence. */
    @Transactional(readOnly = true)
    public Map<String, Object> storyBank(UUID userId, ProfileEngineRequest request) {
        return aiService.storyBank(userId, request);
    }

    /** 10.10 — the target roles this profile could plausibly aim at. */
    @Transactional(readOnly = true)
    public Map<String, Object> roleSuggestions(UUID userId, ProfileEngineRequest request) {
        return aiService.roleSuggestions(userId, request);
    }

    /** 10.6 — skill progress between two snapshots. */
    @Transactional(readOnly = true)
    public Map<String, Object> progress(UUID userId, ProgressRequest request) {
        return aiService.progress(userId, request);
    }
}
