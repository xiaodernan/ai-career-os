package com.careeros.auth.repository;

import com.careeros.auth.entity.RefreshToken;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface RefreshTokenRepository extends JpaRepository<RefreshToken, UUID> {

    Optional<RefreshToken> findByTokenHash(String tokenHash);

    List<RefreshToken> findByFamilyIdAndRevokedAtIsNull(UUID familyId);

    @Modifying
    @Query("""
            update RefreshToken t set t.revokedAt = :now
            where t.userId = :userId and t.revokedAt is null
            """)
    int revokeAllForUser(@Param("userId") UUID userId, @Param("now") OffsetDateTime now);
}
