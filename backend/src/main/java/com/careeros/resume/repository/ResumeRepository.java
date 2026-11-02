package com.careeros.resume.repository;

import com.careeros.resume.entity.Resume;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ResumeRepository extends JpaRepository<Resume, UUID> {

    Page<Resume> findByUserIdOrderByCreatedAtDescIdAsc(UUID userId, Pageable pageable);

    Optional<Resume> findByIdAndUserId(UUID id, UUID userId);

    /**
     * Whether a resume still serves this key as its original upload. The upload stores one object
     * and points two rows at it, so a live resume is a reason to leave the file alone even after
     * its ingested copy is retired.
     */
    boolean existsBySourceFileKey(String sourceFileKey);

    List<Resume> findByUserId(UUID userId);
}
