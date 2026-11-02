package com.careeros.knowledge.repository;

import com.careeros.knowledge.entity.Document;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface DocumentRepository extends JpaRepository<Document, UUID> {

    Optional<Document> findByIdAndUserId(UUID id, UUID userId);

    Optional<Document> findByFileKey(String fileKey);

    /**
     * Whether a row that retrieval can still quote names this key. Retired rows are the ones
     * the delete path left behind, so they are excluded: they keep their key as the audit
     * record, and the audit record is not a reason to hold the bytes.
     */
    boolean existsByFileKeyAndStatusNot(String fileKey, String status);

    List<Document> findBySourceId(UUID sourceId);

    List<Document> findByUserId(UUID userId);
}
