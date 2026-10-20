package com.careeros.ai.service;

import com.careeros.ai.AiServiceClient;
import com.careeros.ai.dto.OutreachRequest;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * The outreach generator (Epic 11.2).
 *
 * <p>The draft is evidence-bound: the validator strips any skill the profile
 * does not support, so a message can only cite what the candidate can back up.
 */
@Service
public class OutreachService {

    private final AiServiceClient aiService;

    public OutreachService(AiServiceClient aiService) {
        this.aiService = aiService;
    }

    /** 11.2 — a referral or networking message for a real person. */
    @Transactional(readOnly = true)
    public Map<String, Object> draft(UUID userId, OutreachRequest request) {
        return aiService.outreach(userId, request);
    }
}
