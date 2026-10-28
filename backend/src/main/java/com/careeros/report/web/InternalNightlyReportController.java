package com.careeros.report.web;

import com.careeros.report.dto.NightlyReportDtos.NightlyReportItem;
import com.careeros.report.dto.NightlyReportDtos.NightlyReportRequest;
import com.careeros.report.service.NightlyReportService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

/**
 * Where the night leaves its record (roadmap 20.1).
 *
 * <p>The nightly job is the only writer and it is not a user: it authenticates with the same
 * shared {@code X-Internal-Token} ai-service uses, through {@code InternalApiFilter}, so this
 * route lives on the internal surface rather than behind a JWT. The row it writes is the one
 * the monitoring page reads back at {@code GET /api/v1/monitoring/nightly-reports}.
 */
@RestController
@RequestMapping("/api/internal/nightly-reports")
public class InternalNightlyReportController {

    private final NightlyReportService reports;

    public InternalNightlyReportController(NightlyReportService reports) {
        this.reports = reports;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public NightlyReportItem record(@RequestBody @Valid NightlyReportRequest request) {
        return reports.record(request);
    }
}
