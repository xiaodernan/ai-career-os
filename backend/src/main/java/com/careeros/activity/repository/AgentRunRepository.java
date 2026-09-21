package com.careeros.activity.repository;

import com.careeros.activity.entity.AgentRun;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface AgentRunRepository extends JpaRepository<AgentRun, UUID> {

    @Query("SELECT r FROM AgentRun r WHERE r.userId = :userId AND (:agent IS NULL OR r.agent = :agent)"
            + " ORDER BY r.startedAt DESC")
    List<AgentRun> findRecent(@Param("userId") UUID userId, @Param("agent") String agent,
                              org.springframework.data.domain.Pageable pageable);

    Optional<AgentRun> findByIdAndUserId(UUID id, UUID userId);

    @Query("SELECT r.status, COUNT(r) FROM AgentRun r WHERE r.userId = :userId GROUP BY r.status")
    List<Object[]> statusCounts(@Param("userId") UUID userId);
}
