package com.careeros.auth.repository;

import com.careeros.auth.entity.UserMfa;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface UserMfaRepository extends JpaRepository<UserMfa, UUID> {

    Optional<UserMfa> findByUserId(UUID userId);
}
