package com.careeros.ai.dto;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.Size;
import java.util.List;

/**
 * The salary & offer wire shapes (Epics 12.1-12.5).
 *
 * <p>Every benchmark is computed against the seeded corpus, so nothing here
 * reaches outside the caller's own offer. The optional fields specialize the
 * question — where to benchmark, which currency, what the candidate is aiming
 * at — and the engine applies its own defaults to whatever is left out.
 */
public final class OfferDtos {

    private OfferDtos() {
    }

    /**
     * 12.1 — salary percentiles for a role, optionally by location and seniority.
     */
    public record SalaryRequest(
            @NotBlank @Size(min = 2, max = 200) String role,
            @Size(max = 120) String location,
            @Size(max = 80) String seniority,
            @Positive Integer targetSalary,
            @Size(min = 3, max = 3) String currency) {
    }

    /**
     * 12.2 — the negotiation coach. `offerBase` is the offer on the table and
     * `matchScore` (0..1) is the candidate's own match against the role, which
     * changes the leverage the coach names.
     */
    public record NegotiationRequest(
            @NotBlank @Size(min = 2, max = 200) String role,
            @Size(max = 120) String location,
            @Size(max = 80) String seniority,
            @Size(min = 3, max = 3) String currency,
            @Positive int offerBase,
            @Min(0) Double matchScore) {
    }

    /** One equity grant, as an offer carries it. */
    public record EquityGrant(
            @Min(0) int shares,
            @Min(0) double strikePrice,
            @Min(0) double currentPrice,
            @Positive Integer vestYears) {
    }

    /** One offer in a comparison: the label names it, the numbers price it. */
    public record OfferItem(
            @NotBlank @Size(min = 1, max = 120) String label,
            @Positive int base,
            @Min(0) int bonus,
            EquityGrant equity) {
    }

    /**
     * 12.3 / 12.5 — compare several offers by total compensation. The equity
     * grant is annualized over its vest, so a cash-only comparison is unchanged
     * by it (12.5).
     */
    public record CompareOffersRequest(
            @NotBlank @Size(min = 2, max = 200) String role,
            @Size(max = 120) String location,
            @Size(max = 80) String seniority,
            @Size(min = 3, max = 3) String currency,
            @Min(0) Double matchScore,
            @NotEmpty @Size(max = 10) List<OfferItem> offers) {
    }

    /**
     * 12.4 — the counter-offer draft: a deterministic anchor plus the reasons
     * behind it, with the model phrasing the reasons.
     */
    public record CounterOfferRequest(
            @NotBlank @Size(min = 2, max = 200) String role,
            @Size(max = 120) String location,
            @Size(max = 80) String seniority,
            @Size(min = 3, max = 3) String currency,
            @Positive int offerBase,
            @Min(0) Double matchScore) {
    }
}
