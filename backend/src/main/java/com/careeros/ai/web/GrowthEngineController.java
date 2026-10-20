package com.careeros.ai.web;

import com.careeros.ai.dto.GrowthEngineRequest;
import com.careeros.ai.dto.ProfileEngineRequest;
import com.careeros.ai.dto.ProgressRequest;
import com.careeros.ai.service.GrowthEngineService;
import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import jakarta.validation.Valid;
import java.util.Map;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * The granular growth engines (Epics 10.1-10.13), each asked on its own.
 *
 * <p>The 10.2 aggregate (`POST /api/v1/growth-report`) composes the same engines
 * for the growth page in one call; these routes are the same engines one at a
 * time, so a caller that wants only the gap analysis does not have to run the
 * whole report to get it.
 *
 * <p>Every answer is the engine's own shape — the bridge forwards the request
 * and owns none of it.
 */
@RestController
@RequestMapping("/api/v1/growth")
public class GrowthEngineController {

    private final GrowthEngineService growth;

    public GrowthEngineController(GrowthEngineService growth) {
        this.growth = growth;
    }

    /** 10.1 — the distance between the profile and the target role. */
    @PostMapping("/gap-analysis")
    public Map<String, Object> gapAnalysis(@CurrentUser AuthUser user,
                                           @RequestBody @Valid GrowthEngineRequest request) {
        return growth.gapAnalysis(user.id(), request);
    }

    /** 10.7 — target-role readiness, as one verdict. */
    @PostMapping("/readiness")
    public Map<String, Object> readiness(@CurrentUser AuthUser user,
                                          @RequestBody @Valid GrowthEngineRequest request) {
        return growth.readiness(user.id(), request);
    }

    /** 10.5 — the phased learning plan that closes the gaps. */
    @PostMapping("/learning-plan")
    public Map<String, Object> learningPlan(@CurrentUser AuthUser user,
                                            @RequestBody @Valid GrowthEngineRequest request) {
        return growth.learningPlan(user.id(), request);
    }

    /** 10.9 — which skills the market asks for, counted from the corpus. */
    @PostMapping("/skill-demand")
    public Map<String, Object> skillDemand(@CurrentUser AuthUser user,
                                            @RequestBody @Valid GrowthEngineRequest request) {
        return growth.skillDemand(user.id(), request);
    }

    /** 10.12 — the gaps ranked by importance and by market pull. */
    @PostMapping("/learning-priority")
    public Map<String, Object> learningPriority(@CurrentUser AuthUser user,
                                                @RequestBody @Valid GrowthEngineRequest request) {
        return growth.learningPriority(user.id(), request);
    }

    /** 10.11 — the stepping-stone roles toward a dream role. */
    @PostMapping("/progression")
    public Map<String, Object> progression(@CurrentUser AuthUser user,
                                            @RequestBody @Valid GrowthEngineRequest request) {
        return growth.progression(user.id(), request);
    }

    /** 10.13 — the pre-interview checklist. */
    @PostMapping("/interview-prep")
    public Map<String, Object> interviewPrep(@CurrentUser AuthUser user,
                                             @RequestBody @Valid GrowthEngineRequest request) {
        return growth.interviewPrep(user.id(), request);
    }

    /** 6.5 — the STAR story bank, drawn from the profile's own evidence. */
    @PostMapping("/story-bank")
    public Map<String, Object> storyBank(@CurrentUser AuthUser user,
                                          @RequestBody @Valid ProfileEngineRequest request) {
        return growth.storyBank(user.id(), request);
    }

    /** 10.10 — the target roles this profile could plausibly aim at. */
    @PostMapping("/role-suggestions")
    public Map<String, Object> roleSuggestions(@CurrentUser AuthUser user,
                                                @RequestBody @Valid ProfileEngineRequest request) {
        return growth.roleSuggestions(user.id(), request);
    }

    /**
     * 10.6 — skill progress between two snapshots. The engine diffs the two gap
     * reports, so the caller supplies the previous one; the growth page gets
     * this for free inside the 10.2 aggregate, and this route is for a caller
     * that already holds a previous answer.
     */
    @PostMapping("/progress")
    public Map<String, Object> progress(@CurrentUser AuthUser user,
                                        @RequestBody @Valid ProgressRequest request) {
        return growth.progress(user.id(), request);
    }
}
