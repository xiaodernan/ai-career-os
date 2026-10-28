package com.careeros.report.service;

import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.common.PageDTO;
import com.careeros.common.Paging;
import com.careeros.report.dto.NightlyReportDtos;
import com.careeros.report.dto.NightlyReportDtos.NightlyReportItem;
import com.careeros.report.dto.NightlyReportDtos.NightlyReportRequest;
import com.careeros.report.entity.NightlyReport;
import com.careeros.report.repository.NightlyReportRepository;
import java.time.OffsetDateTime;
import java.util.Locale;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * The nightly verification history (roadmap 20.1): one observation per night, written once
 * and read back newest first.
 *
 * <p>The invariants a reader relies on are enforced here rather than left to the schema
 * alone, so a malformed report is a sentence with its own code instead of a constraint
 * violation: a report says `passed` or `failed`, and it cannot finish before it started.
 * A night that posts anything else is a caller bug worth failing loudly -- the nightly job
 * is the only writer.
 */
@Service
public class NightlyReportService {

    private final NightlyReportRepository reports;

    public NightlyReportService(NightlyReportRepository reports) {
        this.reports = reports;
    }

    @Transactional
    public NightlyReportItem record(NightlyReportRequest request) {
        String status = request.status().trim().toLowerCase(Locale.ROOT);
        if (!NightlyReport.STATUS_PASSED.equals(status) && !NightlyReport.STATUS_FAILED.equals(status)) {
            throw new ApiException(ApiErrorCode.NIGHTLY_REPORT_STATUS_INVALID,
                    "A nightly report says passed or failed, not '" + request.status() + "'");
        }
        if (request.finishedAt().isBefore(request.startedAt())) {
            throw new ApiException(ApiErrorCode.NIGHTLY_REPORT_CLOCK_REVERSED,
                    "A nightly report cannot finish before it started");
        }
        if (request.summary().size() > NightlyReportDtos.MAX_SUMMARY_KEYS) {
            throw new ApiException(ApiErrorCode.NIGHTLY_REPORT_SUMMARY_TOO_LARGE,
                    "A nightly report summarises at most " + NightlyReportDtos.MAX_SUMMARY_KEYS
                            + " top-level entries");
        }
        NightlyReport row = new NightlyReport();
        row.setSource(request.sourceOrDefault());
        row.setStatus(status);
        row.setCommitSha(request.commitSha());
        row.setRunUrl(request.runUrl());
        row.setStartedAt(request.startedAt());
        row.setFinishedAt(request.finishedAt());
        row.setSummary(request.summary());
        row.setCreatedAt(OffsetDateTime.now());
        return NightlyReportItem.of(reports.save(row));
    }

    @Transactional(readOnly = true)
    public PageDTO<NightlyReportItem> list(int page, int size) {
        Paging.Window window = Paging.of(page, size);
        return PageDTO.from(reports.findAllByOrderByStartedAtDescIdDesc(window.pageable()),
                NightlyReportItem::of);
    }
}
