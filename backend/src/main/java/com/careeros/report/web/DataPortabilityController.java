package com.careeros.report.web;

import com.careeros.ai.AiServiceClient;
import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import com.careeros.report.dto.DataPortabilityDtos.ExportRequest;
import com.careeros.report.dto.DataPortabilityDtos.ImportApplyRequest;
import com.careeros.report.dto.DataPortabilityDtos.ImportPlanRequest;
import com.careeros.report.dto.DataPortabilityDtos.RedactRequest;
import com.careeros.report.dto.DataPortabilityDtos.RenderRequest;
import com.careeros.report.service.ExportService;
import com.careeros.report.service.ImportService;
import jakarta.validation.Valid;
import java.util.Map;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Data portability (13.1-13.3): export, import planning, and section redaction.
 *
 * <p>The ai-service composes the bundle and the import plan; this controller
 * forwards the calls and owns none of the logic. Every route is user-scoped by
 * the ai-service's own {@code X-User-Id} header.
 */
@RestController
@RequestMapping("/api/v1/data-portability")
public class DataPortabilityController {

    private final AiServiceClient aiService;
    private final ExportService exports;
    private final ImportService imports;

    public DataPortabilityController(AiServiceClient aiService, ExportService exports,
                                     ImportService imports) {
        this.aiService = aiService;
        this.exports = exports;
        this.imports = imports;
    }

    /**
     * 13.1 -- export all user data as a versioned, hashed bundle.
     * The bundle is JSON with a content hash, so re-exporting unchanged data
     * yields the same hash.
     */
    @PostMapping("/export")
    public Map<String, Object> exportBundle(@CurrentUser AuthUser user,
                                            @RequestBody(required = false) ExportRequest request) {
        boolean anonymized = request != null && Boolean.TRUE.equals(request.anonymized());
        return exports.exportBundle(user.id(), anonymized);
    }

    /**
     * 13.2 -- plan an idempotent re-import from a bundle.
     * The plan carries per-item content hashes so the backend can skip unchanged rows.
     */
    @PostMapping("/import-plan")
    public Map<String, Object> importPlan(@CurrentUser AuthUser user,
                                           @RequestBody @Valid ImportPlanRequest request) {
        return imports.plan(user.id(), request.bundle(), request.existing());
    }

    /**
     * 13.2 -- apply a re-import. The plan is computed and then executed, and
     * the answer says what was written and which sections were left alone.
     */
    @PostMapping("/import-apply")
    public Map<String, Object> importApply(@CurrentUser AuthUser user,
                                           @RequestBody @Valid ImportApplyRequest request) {
        return imports.apply(user.id(), request.bundle());
    }

    /**
     * 13.3 -- redact sections from a bundle before sharing.
     * The returned bundle has the dropped sections removed and a recomputed hash.
     */
    @PostMapping("/redact")
    public Map<String, Object> redactBundle(@CurrentUser AuthUser user,
                                             @RequestBody @Valid RedactRequest request) {
        return aiService.redactBundle(user.id(), request.bundle(), request.drop());
    }

    /**
     * 13.1 -- the human-readable half: a print-ready document of the bundle.
     * The HTML is self-contained, so the browser can print it straight to PDF.
     *
     * The document is written in the reader's language, so the request says
     * which one: the bundle carries the data and the view carries the words.
     */
    @PostMapping("/render")
    public Map<String, Object> renderBundle(@CurrentUser AuthUser user,
                                             @RequestBody @Valid RenderRequest request) {
        return aiService.renderBundle(user.id(), request.bundle(), request.format(), request.locale());
    }
}
