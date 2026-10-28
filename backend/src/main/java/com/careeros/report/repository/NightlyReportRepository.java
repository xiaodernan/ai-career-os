package com.careeros.report.repository;

import com.careeros.report.entity.NightlyReport;
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
}
