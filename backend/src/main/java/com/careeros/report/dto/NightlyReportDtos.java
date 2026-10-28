package com.careeros.report.dto;

import com.careeros.report.entity.NightlyReport;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * The nightly verification history's shapes (roadmap 20.1).
 *
 * <p>The request is what the night itself posts through the internal token: when it ran, how
 * it ended, and its own account of the steps in `summary`. `summary` stays a map on the way in
 * because the steps belong to the harness, not to this service -- a new key is a new fact
 * rather than a migration. The item is that row read back, with the one key the page renders
 * (`steps`) lifted into a record a client can bind without parsing a free map.
 */
public final class NightlyReportDtos {

    /** Guards the jsonb column against a runaway payload; the nightly posts a handful of steps. */
    public static final int MAX_SUMMARY_KEYS = 40;

    private NightlyReportDtos() {
    }

    public record NightlyReportRequest(
            @NotNull OffsetDateTime startedAt,
            @NotNull OffsetDateTime finishedAt,
            @NotBlank @Size(max = 20) String status,
            @Size(max = 40) String source,
            @Size(max = 64) String commitSha,
            @Size(max = 512) String runUrl,
            @NotNull Map<String, Object> summary) {

        /** The source a report gets when the night does not name one: the scheduled job. */
        public String sourceOrDefault() {
            return source == null || source.isBlank() ? "nightly" : source.trim();
        }
    }

    /**
     * One step of the night, as the read route answers it. The stored summary is the night's
     * own map; this record is the one key of it the page renders. Extraction is lenient on
     * purpose: a step with no name is dropped rather than answered as a blank row, because a
     * row that says nothing still takes the space of one.
     */
    public record NightlyReportStep(String name, String status, String detail) {

        static List<NightlyReportStep> from(Map<String, Object> summary) {
            if (summary == null || !(summary.get("steps") instanceof List<?> rows)) {
                return List.of();
            }
            List<NightlyReportStep> steps = new ArrayList<>();
            for (Object row : rows) {
                if (!(row instanceof Map<?, ?> cell) || cell.get("name") == null) {
                    continue;
                }
                String name = cell.get("name").toString().trim();
                if (name.isEmpty()) {
                    continue;
                }
                steps.add(new NightlyReportStep(name,
                        cell.get("status") == null ? "" : cell.get("status").toString().trim(),
                        cell.get("detail") == null ? null : cell.get("detail").toString()));
            }
            return steps;
        }
    }

    public record NightlyReportItem(
            UUID id,
            String source,
            String status,
            String commitSha,
            String runUrl,
            OffsetDateTime startedAt,
            OffsetDateTime finishedAt,
            List<NightlyReportStep> steps,
            OffsetDateTime createdAt) {

        public static NightlyReportItem of(NightlyReport report) {
            return new NightlyReportItem(report.getId(), report.getSource(), report.getStatus(),
                    report.getCommitSha(), report.getRunUrl(), report.getStartedAt(),
                    report.getFinishedAt(), NightlyReportStep.from(report.getSummary()),
                    report.getCreatedAt());
        }
    }

    /**
     * The install's own verdict (roadmap 20.2): the newest night as a verdict rather than a row,
     * plus the two facts one page of the history cannot show -- whether the answer has been
     * "failed" for several nights running, and whether the newest record is old enough that the
     * cadence itself stopped. A stale verdict is an alarm even when the newest night passed: a
     * record that stopped arriving is the failure nothing wrote down.
     */
    public record NightlyVerdict(
            String status,
            OffsetDateTime finishedAt,
            String commitSha,
            String runUrl,
            int consecutiveFailures,
            boolean stale,
            int staleAfterHours) {

        /** The status of a history with no rows: not a night's own word, the absence of one. */
        public static final String MISSING = "missing";
    }
}
