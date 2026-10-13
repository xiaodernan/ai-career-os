package com.careeros.ai.web;

import com.careeros.ai.AiServiceClient;
import com.careeros.ai.dto.GrowthReportRequest;
import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import jakarta.validation.Valid;
import java.util.Map;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * The browser's surface over the growth-report aggregate (roadmap 10.2, the first bridge over
 * the seventeen internal engines).
 *
 * <p>The engine composes readiness, gap, salary, learning plan and progress in one call so the
 * bridge carries one request rather than seven round trips; this route answers the report the
 * engine built, in the engine's own shape. Nothing here re-models it — the ai-service pins that
 * schema with {@code test_forward_features_contract}, and a second copy of it on this side would
 * drift from the thing that owns it. The plan's persistence (10.4) will add a write below this
 * route when it lands; the report itself is computed, not stored, so there is nothing to GET yet.
 */
@RestController
@RequestMapping("/api/v1/growth-report")
public class GrowthController {

    private final AiServiceClient ai;

    public GrowthController(AiServiceClient ai) {
        this.ai = ai;
    }

    @PostMapping
    public Map<String, Object> report(@CurrentUser AuthUser user,
                                      @RequestBody @Valid GrowthReportRequest request) {
        return ai.growthReport(request, user.id());
    }
}
