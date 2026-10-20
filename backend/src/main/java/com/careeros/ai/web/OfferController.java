package com.careeros.ai.web;

import com.careeros.ai.dto.OfferDtos.CompareOffersRequest;
import com.careeros.ai.dto.OfferDtos.CounterOfferRequest;
import com.careeros.ai.dto.OfferDtos.NegotiationRequest;
import com.careeros.ai.dto.OfferDtos.SalaryRequest;
import com.careeros.ai.service.OfferService;
import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import jakarta.validation.Valid;
import java.util.Map;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Salary & offer intelligence (Epics 12.1-12.5).
 *
 * <p>Every answer is a deterministic read of the seeded corpus against the
 * caller's own offer — no model invents a number here. This route forwards the
 * request and answers the engine's shape.
 */
@RestController
@RequestMapping("/api/v1/offers")
public class OfferController {

    private final OfferService offers;

    public OfferController(OfferService offers) {
        this.offers = offers;
    }

    /** 12.1 — salary percentiles for a role. */
    @PostMapping("/salary-benchmark")
    public Map<String, Object> salaryBenchmark(@CurrentUser AuthUser user,
                                                @RequestBody @Valid SalaryRequest request) {
        return offers.salaryBenchmark(user.id(), request);
    }

    /** 12.2 — the negotiation coach: leverage plus the talking points. */
    @PostMapping("/negotiate")
    public Map<String, Object> negotiate(@CurrentUser AuthUser user,
                                          @RequestBody @Valid NegotiationRequest request) {
        return offers.negotiate(user.id(), request);
    }

    /** 12.3 / 12.5 — several offers ranked by total compensation. */
    @PostMapping("/compare")
    public Map<String, Object> compare(@CurrentUser AuthUser user,
                                        @RequestBody @Valid CompareOffersRequest request) {
        return offers.compareOffers(user.id(), request);
    }

    /** 12.4 — the counter-offer draft. */
    @PostMapping("/counter-offer")
    public Map<String, Object> counterOffer(@CurrentUser AuthUser user,
                                             @RequestBody @Valid CounterOfferRequest request) {
        return offers.counterOffer(user.id(), request);
    }
}
