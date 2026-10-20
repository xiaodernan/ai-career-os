package com.careeros.ai.repository;

import com.careeros.ai.entity.GrowthPlan;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

/**
 * One row per growth-report run. The only read the feature needs is the latest row for
 * a (user, role) pair — the `previous` the next run diffs against — so that is the one
 * finder here, and the index in V9 is shaped for exactly it.
 *
 * The export (13.1) needs every one of the user's rows, not the latest, so a
 * second finder walks them newest first.
 */
public interface GrowthPlanRepository extends JpaRepository<GrowthPlan, UUID> {

    Optional<GrowthPlan> findFirstByUserIdAndTargetRoleIgnoreCaseOrderByCreatedAtDesc(
            UUID userId, String targetRole);

    /** Every stored run for the user, newest first — the export's own section. */
    List<GrowthPlan> findByUserIdOrderByCreatedAtDesc(UUID userId);
}
