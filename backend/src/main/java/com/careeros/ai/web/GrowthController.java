package com.careeros.ai.web;

import com.careeros.ai.dto.GrowthReportRequest;
import com.careeros.ai.service.GrowthService;
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
 * drift from the thing that owns it. Since 10.4 the service behind this route also stores each
 * run and feeds the stored one back as the next run's `previous`, so the progress block diffs
 * server-side and the browser no longer has to carry its last answer around.
 */
@RestController
@RequestMapping("/api/v1/growth-report")
public class GrowthController {

    private final GrowthService growth;

    public GrowthController(GrowthService growth) {
        this.growth = growth;
    }

    @PostMapping
    public Map<String, Object> report(@CurrentUser AuthUser user,
                                      @RequestBody @Valid GrowthReportRequest request) {
        return growth.report(user.id(), request);
    }
}
