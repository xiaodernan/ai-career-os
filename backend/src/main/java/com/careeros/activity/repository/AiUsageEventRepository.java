package com.careeros.activity.repository;

import com.careeros.activity.entity.AiUsageEvent;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface AiUsageEventRepository extends JpaRepository<AiUsageEvent, Long> {

    @Query("SELECT COALESCE(SUM(u.costUsd), 0), COALESCE(SUM(u.inputTokens), 0),"
            + " COALESCE(SUM(u.outputTokens), 0), COALESCE(SUM(u.cachedTokens), 0), COUNT(u)"
            + " FROM AiUsageEvent u WHERE u.userId = :userId AND u.createdAt >= :since")
    List<Object[]> usageTotalsSince(@Param("userId") UUID userId,
                                    @Param("since") java.time.OffsetDateTime since);

    @Query("SELECT u.model, SUM(u.inputTokens), SUM(u.outputTokens), SUM(u.cachedTokens),"
            + " SUM(u.costUsd), COUNT(u) FROM AiUsageEvent u WHERE u.userId = :userId GROUP BY u.model")
    List<Object[]> usageByModel(@Param("userId") UUID userId);
}
