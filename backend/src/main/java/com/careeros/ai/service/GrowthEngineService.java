package com.careeros.ai.service;

import com.careeros.ai.AiServiceClient;
import com.careeros.ai.dto.GrowthEngineRequest;
import com.careeros.ai.dto.ProfileEngineRequest;
import com.careeros.ai.dto.ProgressRequest;
import java.util.Map;
import java.util.UUID;
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

    public GrowthEngineService(AiServiceClient aiService) {
        this.aiService = aiService;
    }

    /** 10.1 — the distance between the profile and the target role. */
    @Transactional(readOnly = true)
    public Map<String, Object> gapAnalysis(UUID userId, GrowthEngineRequest request) {
        return aiService.gapAnalysis(userId, request);
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
