package com.careeros.ai.service;

import com.careeros.ai.AiServiceClient;
import com.careeros.ai.dto.OfferDtos.CompareOffersRequest;
import com.careeros.ai.dto.OfferDtos.CounterOfferRequest;
import com.careeros.ai.dto.OfferDtos.NegotiationRequest;
import com.careeros.ai.dto.OfferDtos.OfferItem;
import com.careeros.ai.dto.OfferDtos.SalaryRequest;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Salary & offer intelligence (Epics 12.1-12.5).
 *
 * <p>Every answer is a deterministic read of the seeded corpus against the
 * caller's own offer, so this service forwards the request and owns none of the
 * logic. The engines live in ai-service; a second copy of the arithmetic here
 * would be a second answer to the same question.
 */
@Service
public class OfferService {

    private final AiServiceClient aiService;

    public OfferService(AiServiceClient aiService) {
        this.aiService = aiService;
    }

    /** 12.1 — salary percentiles for a role. */
    @Transactional(readOnly = true)
    public Map<String, Object> salaryBenchmark(UUID userId, SalaryRequest request) {
        return aiService.salaryBenchmark(userId, request);
    }

    /** 12.2 — the negotiation coach: leverage plus the talking points. */
    @Transactional(readOnly = true)
    public Map<String, Object> negotiate(UUID userId, NegotiationRequest request) {
        return aiService.negotiate(userId, request);
    }

    /** 12.3 / 12.5 — several offers ranked by total compensation. */
    @Transactional(readOnly = true)
    public Map<String, Object> compareOffers(UUID userId, CompareOffersRequest request) {
        return aiService.compareOffers(userId, request);
    }

    /** 12.4 — the counter-offer draft. */
    @Transactional(readOnly = true)
    public Map<String, Object> counterOffer(UUID userId, CounterOfferRequest request) {
        return aiService.counterOffer(userId, request);
    }
}
