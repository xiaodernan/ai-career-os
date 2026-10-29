package com.careeros.inbound.repository;

import com.careeros.inbound.entity.InboundMail;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface InboundMailRepository extends JpaRepository<InboundMail, UUID> {

    Optional<InboundMail> findByUserIdAndMessageKey(UUID userId, String messageKey);
}
