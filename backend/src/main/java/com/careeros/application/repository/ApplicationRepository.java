package com.careeros.application.repository;

import com.careeros.application.entity.Application;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface ApplicationRepository extends JpaRepository<Application, UUID> {

    Optional<Application> findByIdAndUserId(UUID id, UUID userId);

    Page<Application> findByUserIdAndStatusOrderByPositionAscIdAsc(UUID userId, String status, Pageable pageable);

    Page<Application> findByUserIdOrderByUpdatedAtDescIdAsc(UUID userId, Pageable pageable);

    List<Application> findByUserIdAndJobId(UUID userId, UUID jobId);

    long countByUserId(UUID userId);

    long countByUserIdAndStatus(UUID userId, String status);

    @Query("SELECT a.status, COUNT(a) FROM Application a WHERE a.userId = :userId GROUP BY a.status")
    List<Object[]> statusCounts(@Param("userId") UUID userId);

    /**
     * Every account with at least one application -- the weekly letter's audience (19.4). A
     * user with no applications has nothing a week can say; their first letter arrives once
     * they have something to report.
     */
    @Query("SELECT DISTINCT a.userId FROM Application a")
    List<UUID> distinctUserIds();
}
