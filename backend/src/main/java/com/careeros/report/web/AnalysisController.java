package com.careeros.report.web;

import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import com.careeros.report.service.AnalysisService;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * The weekly insight digest (15.3): stalled applications, live stage mix, and
 * headline rates, composed by the ai-service's analytics engine.
 *
 * <p>The digest is read-only and deterministic — the engine reads the user's own
 * application history and computes metrics without a model. This route answers
 * the digest the engine built, in the engine's own shape.
 */
@RestController
@RequestMapping("/api/v1/analysis")
public class AnalysisController {

    private final AnalysisService analysis;

    public AnalysisController(AnalysisService analysis) {
        this.analysis = analysis;
    }

    /**
     * The reader's language travels as {@code locale}: the digest's sentences are
     * the only words in the answer, so the page's locale has to reach the engine.
     * Absent means the product default, which the engine owns.
     */
    @GetMapping("/insight-digest")
    public Map<String, Object> insightDigest(@CurrentUser AuthUser user,
            @RequestParam(name = "locale", required = false) String locale) {
        return analysis.insightDigest(user.id(), locale);
    }

    /**
     * 15.1 — the pipeline funnel: how many applications reached each stage, and
     * where the leak is.
     */
    @GetMapping("/pipeline-funnel")
    public Map<String, Object> pipelineFunnel(@CurrentUser AuthUser user) {
        return analysis.pipelineFunnel(user.id());
    }

    /**
     * 15.2 — the reply / interview / offer rates and the per-stage durations.
     * A rejection counts as a response: a no is still an answer.
     */
    @GetMapping("/response-rate")
    public Map<String, Object> responseRate(@CurrentUser AuthUser user) {
        return analysis.responseRate(user.id());
    }
}
