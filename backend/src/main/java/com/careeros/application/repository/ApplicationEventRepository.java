package com.careeros.application.repository;

import com.careeros.application.entity.ApplicationEvent;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface ApplicationEventRepository extends JpaRepository<ApplicationEvent, UUID> {

    List<ApplicationEvent> findByApplicationIdOrderByCreatedAtDesc(UUID applicationId);

    /**
     * Newest first, and {@code id} last. The dashboard's activity preview is a capped window
     * rather than a board, but a window all the same: a status change and the note written
     * beside it land in the same second often enough, so without the tie-break the same
     * five-row request can serve a row twice or drop one. The name keeps its derived
     * spelling -- renaming it would churn a caller another unit is editing -- and the
     * statement below is what runs, the same shape {@code AgentRunRepository.findRecent}
     * uses for the activity feed.
     */
    @Query("SELECT e FROM ApplicationEvent e WHERE e.userId = :userId "
            + "ORDER BY e.createdAt DESC, e.id ASC")
    List<ApplicationEvent> findByUserIdOrderByCreatedAtDesc(@Param("userId") UUID userId,
            org.springframework.data.domain.Pageable pageable);

    /**
     * Every transition of one kind the caller's applications have been through, oldest
     * first. This one has no {@code Pageable} on purpose: a duration is measured from the
     * <em>first</em> time a stage was reached, so trimming an ascending window would cut
     * away exactly the rows that carry the answer. {@code Id} is the last key so two
     * transitions written in the same second cannot trade places -- the same total-order
     * rule the activity preview above earns with an explicit {@code @Query}.
     */
    List<ApplicationEvent> findByUserIdAndKindOrderByCreatedAtAscIdAsc(UUID userId, String kind);
}
