package com.careeros.knowledge.repository;

import com.careeros.knowledge.entity.Document;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface DocumentRepository extends JpaRepository<Document, UUID> {

    Optional<Document> findByIdAndUserId(UUID id, UUID userId);

    Optional<Document> findByFileKey(String fileKey);

    List<Document> findBySourceId(UUID sourceId);

    List<Document> findByUserId(UUID userId);
}
