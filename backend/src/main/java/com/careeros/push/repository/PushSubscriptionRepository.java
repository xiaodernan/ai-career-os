package com.careeros.push.repository;

import com.careeros.push.entity.PushSubscription;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

/** The browser registrations an account can be woken through (roadmap 33.1). */
public interface PushSubscriptionRepository extends JpaRepository<PushSubscription, UUID> {

    /** The morning ring's audience (roadmap 33.3): every account with at least one browser. */
    @Query("select distinct s.userId from PushSubscription s")
    List<UUID> distinctUserIds();

    Optional<PushSubscription> findByEndpointUrl(String endpointUrl);

    List<PushSubscription> findByUserIdOrderByCreatedAtDesc(UUID userId);

    Optional<PushSubscription> findByIdAndUserId(UUID id, UUID userId);

    long countByUserId(UUID userId);

    void deleteByUserId(UUID userId);
}
