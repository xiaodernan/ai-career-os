package com.careeros.ai.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.Size;
import java.util.Map;

/**
 * The growth page's one request, bound for `POST /internal/features/growth-report`.
 *
 * <p>`targetRole` is the only required field: every engine the report composes (gap 10.1,
 * salary 12.1, readiness 10.7, learning plan 10.5, progress 10.6) is anchored on the role
 * the user is aiming at, and the ai-service validates the same ten-character floor. The
 * optionals specialize the report — where to benchmark, what currency, which resume version
 * to read — and `previous` is the prior report's own shape, so progress can diff against
 * what the user saw last time rather than against a summary this bridge would have to
 * invent. It is forwarded untouched: the report's schema is the ai-service's, and a
 * re-modelled copy here would drift from the engine that owns it.
 */
public record GrowthReportRequest(
        @NotBlank @Size(min = 10, max = 200) String targetRole,
        @Size(max = 80) String seniority,
        String resumeVersionId,
        @Size(max = 120) String location,
        @Size(min = 3, max = 3) String currency,
        @Positive Integer targetSalary,
        Map<String, Object> previous) {
}
