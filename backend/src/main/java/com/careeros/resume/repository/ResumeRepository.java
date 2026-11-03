package com.careeros.resume.repository;

import com.careeros.resume.entity.Resume;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

public interface ResumeRepository extends JpaRepository<Resume, UUID> {

    Page<Resume> findByUserIdOrderByCreatedAtDescIdAsc(UUID userId, Pageable pageable);

    Optional<Resume> findByIdAndUserId(UUID id, UUID userId);

    /**
     * Whether a resume still serves this key as its original upload. The upload stores one object
     * and points two rows at it, so a live resume is a reason to leave the file alone even after
     * its ingested copy is retired.
     */
    boolean existsBySourceFileKey(String sourceFileKey);

    /**
     * Every key any resume row serves as its original upload, with no status filter because the
     * row has no status to filter on (roadmap 48.2). A resume keeps its upload for as long as the
     * resume row exists: the detail page hands back the bytes that key names, so a sweep that
     * missed this read would delete a file a reader can still open.
     */
    @Query("select r.sourceFileKey from Resume r where r.sourceFileKey is not null")
    List<String> findAllSourceFileKeys();

    List<Resume> findByUserId(UUID userId);
}
