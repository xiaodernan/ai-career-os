package com.careeros.report.service;

import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.common.PageDTO;
import com.careeros.common.Paging;
import com.careeros.report.dto.NightlyReportDtos;
import com.careeros.report.dto.NightlyReportDtos.NightlyReportItem;
import com.careeros.report.dto.NightlyReportDtos.NightlyReportRequest;
import com.careeros.report.dto.NightlyReportDtos.NightlyVerdict;
import com.careeros.report.entity.NightlyReport;
import com.careeros.report.repository.NightlyReportRepository;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Locale;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
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
 *
 * <p>Each write also republishes the verdict as gauges (roadmap 20.3), so the alarm stack
 * hears the same answer the monitoring page draws, and a boot reads it once more from the
 * stored history.
 */
@Service
public class NightlyReportService {

    private static final Logger log = LoggerFactory.getLogger(NightlyReportService.class);

    /**
     * A daily job plus slack: a newest record older than this means the cadence stopped rather
     * than that one night ran late. The scheduled run starts at 03:20 and takes under an hour, so
     * a day and a half is more than twice the expected gap.
     */
    static final int STALE_AFTER_HOURS = 36;
    /** How far back the streak walk looks; a longer streak is already "it keeps failing". */
    static final int STREAK_WINDOW = 30;

    private final NightlyReportRepository reports;
    private final NightlyVerdictMetrics metrics;

    public NightlyReportService(NightlyReportRepository reports, NightlyVerdictMetrics metrics) {
        this.reports = reports;
        this.metrics = metrics;
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
        NightlyReportItem item = NightlyReportItem.of(reports.save(row));
        metrics.publish(verdict());
        return item;
    }

    @Transactional(readOnly = true)
    public PageDTO<NightlyReportItem> list(int page, int size) {
        Paging.Window window = Paging.of(page, size);
        return PageDTO.from(reports.findAllByOrderByStartedAtDescIdDesc(window.pageable()),
                NightlyReportItem::of);
    }

    /**
     * Whether the install verified itself, as one answer. The walk is newest first, so the
     * streak ends at the first night that is not a failure; the staleness is measured from the
     * newest finish, because a night that is itself still running has not left a row yet.
     */
    @Transactional(readOnly = true)
    public NightlyVerdict verdict() {
        List<NightlyReport> newest = reports
                .findAllByOrderByStartedAtDescIdDesc(Paging.first(STREAK_WINDOW))
                .getContent();
        if (newest.isEmpty()) {
            return new NightlyVerdict(NightlyVerdict.MISSING, null, null, null, 0, true,
                    STALE_AFTER_HOURS);
        }
        NightlyReport latest = newest.get(0);
        int streak = 0;
        for (NightlyReport report : newest) {
            if (!NightlyReport.STATUS_FAILED.equals(report.getStatus())) {
                break;
            }
            streak++;
        }
        boolean stale = latest.getFinishedAt().plusHours(STALE_AFTER_HOURS)
                .isBefore(OffsetDateTime.now());
        return new NightlyVerdict(latest.getStatus(), latest.getFinishedAt(),
                latest.getCommitSha(), latest.getRunUrl(), streak, stale, STALE_AFTER_HOURS);
    }

    /**
     * One read at boot so a restart does not silence a streak the database still holds. The
     * gauges keep their boot defaults if the read fails: a scrape endpoint is not worth a
     * process that will not start, and a marker that stays at boot is the documented grace.
     */
    @EventListener(ApplicationReadyEvent.class)
    public void publishStartupVerdict() {
        try {
            metrics.publish(verdict());
        } catch (RuntimeException ex) {
            log.warn("the nightly verdict gauges keep their boot defaults: the startup read failed", ex);
        }
    }
}
