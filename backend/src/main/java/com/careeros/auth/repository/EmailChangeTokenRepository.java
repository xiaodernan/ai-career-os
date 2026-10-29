package com.careeros.auth.repository;

import com.careeros.auth.entity.EmailChangeToken;
import java.time.OffsetDateTime;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.transaction.annotation.Transactional;

public interface EmailChangeTokenRepository extends JpaRepository<EmailChangeToken, UUID> {

    Optional<EmailChangeToken> findByTokenHash(String tokenHash);

    void deleteByUserId(UUID userId);

    /** Expired address-move rows past the retention cutoff (roadmap 28.1), own transaction. */
    @Modifying
    @Transactional
    @Query("delete from EmailChangeToken t where t.expiresAt < :cutoff")
    int deleteExpiredBefore(@Param("cutoff") OffsetDateTime cutoff);
}
