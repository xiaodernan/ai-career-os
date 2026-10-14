package com.careeros.network.repository;

import com.careeros.network.entity.Contact;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

/**
 * The registry's reads: one user's people, most recently touched first (the order the
 * page renders and the order "who have I not talked to" asks about), and the
 * user-scoped single find every mutation is anchored on.
 */
public interface ContactRepository extends JpaRepository<Contact, UUID> {

    List<Contact> findByUserIdOrderByUpdatedAtDesc(UUID userId);

    Optional<Contact> findByIdAndUserId(UUID id, UUID userId);
}
