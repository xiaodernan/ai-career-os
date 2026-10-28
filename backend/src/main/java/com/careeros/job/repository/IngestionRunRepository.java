package com.careeros.job.repository;

import com.careeros.job.entity.IngestionRun;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import jakarta.persistence.LockModeType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;

public interface IngestionRunRepository extends JpaRepository<IngestionRun, UUID> {

    /**
     * The run history, newest first. `id` is the tiebreak because `started_at` is not unique:
     * a sweep that pulls two feeds in the same millisecond otherwise leaves their order to the
     * plan, and the same page answers different rows on two visits.
     */
    Page<IngestionRun> findByUserIdOrderByStartedAtDescIdDesc(UUID userId, Pageable pageable);

    Optional<IngestionRun> findFirstByFeedIdOrderByStartedAtDesc(UUID feedId);

    Optional<IngestionRun> findByIdAndUserId(UUID id, UUID userId);

    /**
     * The apply's read: the owner's run, locked for the whole transaction. Two presses of
     * the button arrive as two transactions; the second waits on this row and then sees
     * the receipt the first wrote, so the plan cannot be written to the board twice.
     */
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    Optional<IngestionRun> findWithLockByIdAndUserId(UUID id, UUID userId);
}
