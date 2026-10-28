package com.careeros.auth.repository;

import com.careeros.auth.entity.EmailChangeToken;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface EmailChangeTokenRepository extends JpaRepository<EmailChangeToken, UUID> {

    Optional<EmailChangeToken> findByTokenHash(String tokenHash);

    void deleteByUserId(UUID userId);
}
