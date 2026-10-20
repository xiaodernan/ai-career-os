package com.careeros.ai.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.Size;

/**
 * The company-brief request (Epic 4.8).
 *
 * <p>The brief is a deterministic read of the seeded corpus — what the postings
 * for one company say about it — so the only field it needs is the company's
 * name, and how many rows the answer should carry.
 */
public record CompanyBriefRequest(
        @NotBlank @Size(min = 2, max = 200) String company,
        @Positive Integer top) {
}
