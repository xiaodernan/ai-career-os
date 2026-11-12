package com.careeros.notification.repository;

import com.careeros.notification.entity.NotificationState;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface NotificationStateRepository extends JpaRepository<NotificationState, NotificationState.Key> {

    /** The inbox reads every state it has, once, rather than one lookup per synthesized item. */
    List<NotificationState> findByUserId(UUID userId);

    /**
     * One round trip for a batch of episodes. The latch paths and the mark-read walks all
     * start from the inbox's own visible set (bounded by {@code INBOX_LIMIT}), so the keys
     * are few and known to be worth loading together instead of one select per key.
     */
    List<NotificationState> findByUserIdAndSignalKeyIn(UUID userId, List<String> signalKeys);
}
