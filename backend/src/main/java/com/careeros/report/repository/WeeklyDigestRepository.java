package com.careeros.report.repository;

import com.careeros.report.entity.WeeklyDigest;
import java.time.LocalDate;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface WeeklyDigestRepository extends JpaRepository<WeeklyDigest, UUID> {

    List<WeeklyDigest> findByUserIdOrderByWeekStartDesc(UUID userId, Pageable pageable);

    Optional<WeeklyDigest> findByUserIdAndWeekStart(UUID userId, LocalDate weekStart);
}
