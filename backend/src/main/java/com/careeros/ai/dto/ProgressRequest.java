package com.careeros.ai.dto;

import jakarta.validation.constraints.Size;
import java.util.Map;

/**
 * The skill-progress request (Epic 10.6).
 *
 * <p>The progress engine diffs two gap reports: the current one it computes
 * from the resume, and the previous one the caller holds. The previous report is
 * a prior answer's own shape, so it travels as a free-form map — a re-modelled
 * copy here would drift from the engine that produces it.
 */
public record ProgressRequest(
        @Size(min = 10, max = 200) String targetRole,
        @Size(max = 80) String seniority,
        String resumeVersionId,
        /** The prior gap report, in the engine's own shape. */
        Map<String, Object> previous) {
}
