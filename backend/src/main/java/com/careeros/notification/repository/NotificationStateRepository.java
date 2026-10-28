package com.careeros.notification.repository;

import com.careeros.notification.entity.NotificationState;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface NotificationStateRepository extends JpaRepository<NotificationState, NotificationState.Key> {

    /** The inbox reads every state it has, once, rather than one lookup per synthesized item. */
    List<NotificationState> findByUserId(UUID userId);

    Optional<NotificationState> findByUserIdAndSignalKey(UUID userId, String signalKey);
}
