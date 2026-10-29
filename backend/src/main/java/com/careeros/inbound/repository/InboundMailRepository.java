package com.careeros.inbound.repository;

import com.careeros.inbound.entity.InboundMail;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface InboundMailRepository extends JpaRepository<InboundMail, UUID> {

    Optional<InboundMail> findByUserIdAndMessageKey(UUID userId, String messageKey);

    Optional<InboundMail> findByIdAndUserId(UUID id, UUID userId);

    /** The replies page: one account's letters newest first. */
    Page<InboundMail> findByUserIdOrderByReceivedAtDescIdDesc(UUID userId, Pageable pageable);

    /** What the inbox may carry (37.3): the letters already filed on an application. */
    List<InboundMail> findByUserIdAndApplicationIdIsNotNullOrderByReceivedAtDescIdDesc(
            UUID userId, Pageable pageable);
}
