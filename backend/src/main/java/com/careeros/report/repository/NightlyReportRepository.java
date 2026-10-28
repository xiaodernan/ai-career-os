package com.careeros.report.repository;

import com.careeros.report.entity.NightlyReport;
import java.time.OffsetDateTime;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface NightlyReportRepository extends JpaRepository<NightlyReport, UUID> {

    /**
     * The history, newest first. `id` is the tiebreak because a manual dispatch can start in
     * the same second as the scheduled run, and the same page must answer the same order.
     */
    Page<NightlyReport> findAllByOrderByStartedAtDescIdDesc(Pageable pageable);

    /**
     * One night is one row. A retried POST repeats every field, so the source and the span find
     * the row the first attempt wrote; a re-run has new timestamps and is therefore another
     * attempt. The lookup is not a database constraint -- the only writer is one job and its
     * retries are sequential -- but it is what makes the recorder safe to retry.
     */
    Optional<NightlyReport> findBySourceAndStartedAtAndFinishedAt(
            String source, OffsetDateTime startedAt, OffsetDateTime finishedAt);
}
