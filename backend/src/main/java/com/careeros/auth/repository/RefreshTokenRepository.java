package com.careeros.auth.repository;

import com.careeros.auth.entity.RefreshToken;
import java.time.OffsetDateTime;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.transaction.annotation.Transactional;

public interface RefreshTokenRepository extends JpaRepository<RefreshToken, UUID> {

    Optional<RefreshToken> findByTokenHash(String tokenHash);

    List<RefreshToken> findByFamilyIdAndRevokedAtIsNull(UUID familyId);

    List<RefreshToken> findByUserIdAndRevokedAtIsNullAndExpiresAtAfter(
            UUID userId, OffsetDateTime now);

    List<RefreshToken> findByFamilyIdIn(Collection<UUID> familyIds);

    @Modifying
    @Query("""
            update RefreshToken t set t.revokedAt = :now
            where t.userId = :userId and t.revokedAt is null
            """)
    int revokeAllForUser(@Param("userId") UUID userId, @Param("now") OffsetDateTime now);

    /**
     * Rows whose token expired before the cutoff (roadmap 28.1). The sweep's own
     * transaction: a slow delete on this table must not hold the other two.
     */
    @Modifying
    @Transactional
    @Query("delete from RefreshToken t where t.expiresAt < :cutoff")
    int deleteExpiredBefore(@Param("cutoff") OffsetDateTime cutoff);
}
