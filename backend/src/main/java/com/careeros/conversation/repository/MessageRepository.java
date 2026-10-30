package com.careeros.conversation.repository;

import com.careeros.conversation.entity.Message;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface MessageRepository extends JpaRepository<Message, UUID> {

    List<Message> findByConversationIdOrderByCreatedAtAsc(UUID conversationId);

    /** The export's read: every transcript in one page of chats, one statement. */
    List<Message> findByConversationIdInOrderByCreatedAtAscIdAsc(List<UUID> conversationIds);

    List<Message> findByConversationIdOrderByCreatedAtDescIdAsc(UUID conversationId, Pageable pageable);

    Optional<Message> findFirstByConversationIdAndRoleOrderByCreatedAtDesc(UUID conversationId, String role);

    long countByConversationId(UUID conversationId);
}
