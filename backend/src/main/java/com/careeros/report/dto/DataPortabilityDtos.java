package com.careeros.report.dto;

import com.fasterxml.jackson.annotation.JsonAlias;
import jakarta.validation.constraints.Size;
import java.util.List;
import java.util.Map;

/**
 * The data-portability wire shapes (13.1-13.3).
 *
 * <p>Each record is the browser's request, bound by name. The bundle itself is a
 * free-form document — the ai-service owns its schema and its content hash — so it
 * travels as a `Map` rather than a re-modelled copy that could drift from the
 * engine that produces it.
 */
public final class DataPortabilityDtos {

    private DataPortabilityDtos() {
    }

    /**
     * 13.1 -- export everything. `anonymized` strips the profile's PII fields
     * before the bundle is built; it is a request flag, not a second export shape.
     */
    public record ExportRequest(Boolean anonymized) {
    }

    /**
     * 13.2 -- plan a re-import. `existing` is the user's current state, exported
     * the same way, so the plan can tell a create from an update and a delete
     * from a row that was never there.
     */
    public record ImportPlanRequest(Map<String, Object> bundle,
                                    Map<String, Object> existing) {
    }

    /**
     * 13.2 -- apply a re-import. The bundle is the document being restored; the
     * plan is computed from it and the current state, and the ops are executed.
     */
    public record ImportApplyRequest(Map<String, Object> bundle) {
    }

    /**
     * 13.3 -- redact sections. `drop` names the sections to remove; the
     * ai-service rejects a name it does not know rather than silently dropping
     * the wrong section.
     */
    public record RedactRequest(Map<String, Object> bundle,
                                 @Size(max = 16) List<String> drop) {
    }

    /**
     * 13.1 -- render the bundle as a document. `format` is "html" or "pdf";
     * the PDF converter is an optional dependency, so a build without it
     * answers the HTML -- which is already print-ready -- and says why.
     */
    public record RenderRequest(Map<String, Object> bundle,
                                @Size(max = 8) String format) {
    }
}
