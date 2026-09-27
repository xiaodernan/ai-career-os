package com.careeros.knowledge.repository;

import com.careeros.knowledge.entity.KnowledgeSource;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface KnowledgeSourceRepository extends JpaRepository<KnowledgeSource, UUID> {

    Page<KnowledgeSource> findByUserIdOrderByCreatedAtDesc(UUID userId, Pageable pageable);

    /** The source a citation points at: a chunk's document_id is this column, not the row's own id. */
    Page<KnowledgeSource> findByUserIdAndDocumentIdOrderByCreatedAtDesc(UUID userId, UUID documentId,
                                                                        Pageable pageable);

    Optional<KnowledgeSource> findByIdAndUserId(UUID id, UUID userId);

    Optional<KnowledgeSource> findFirstByUserIdAndKindAndRefId(UUID userId, String kind, UUID refId);
    List<KnowledgeSource> findByUserIdAndKindAndRefId(UUID userId, String kind, UUID refId);

    List<KnowledgeSource> findByUserId(UUID userId);
}
