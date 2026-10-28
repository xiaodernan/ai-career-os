package com.careeros.job.repository;

import com.careeros.job.entity.IngestionRun;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface IngestionRunRepository extends JpaRepository<IngestionRun, UUID> {

    List<IngestionRun> findByUserIdOrderByStartedAtDesc(UUID userId, Pageable pageable);

    Optional<IngestionRun> findFirstByFeedIdOrderByStartedAtDesc(UUID feedId);

    Optional<IngestionRun> findByIdAndUserId(UUID id, UUID userId);
}
