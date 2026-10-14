package com.careeros.ai.repository;

import com.careeros.ai.entity.GrowthPlan;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

/**
 * One row per growth-report run. The only read the feature needs is the latest row for
 * a (user, role) pair — the `previous` the next run diffs against — so that is the one
 * finder here, and the index in V9 is shaped for exactly it.
 */
public interface GrowthPlanRepository extends JpaRepository<GrowthPlan, UUID> {

    Optional<GrowthPlan> findFirstByUserIdAndTargetRoleIgnoreCaseOrderByCreatedAtDesc(
            UUID userId, String targetRole);
}
