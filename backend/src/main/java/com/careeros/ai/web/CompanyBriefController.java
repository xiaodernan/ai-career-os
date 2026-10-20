package com.careeros.ai.web;

import com.careeros.ai.AiServiceClient;
import com.careeros.ai.dto.CompanyBriefRequest;
import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import jakarta.validation.Valid;
import java.util.Map;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * The company brief (Epic 4.8).
 *
 * <p>A deterministic read of the seeded corpus: what the postings for one
 * company say about it. No model, so no invention — a company the corpus does
 * not carry answers with no rows rather than a plausible summary.
 */
@RestController
@RequestMapping("/api/v1/companies")
public class CompanyBriefController {

    private final AiServiceClient aiService;

    public CompanyBriefController(AiServiceClient aiService) {
        this.aiService = aiService;
    }

    @PostMapping("/brief")
    public Map<String, Object> brief(@CurrentUser AuthUser user,
                                     @RequestBody @Valid CompanyBriefRequest request) {
        return aiService.companyBrief(user.id(), request);
    }
}
