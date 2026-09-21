package com.careeros.resume.repository;

import com.careeros.resume.entity.ResumeVersion;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ResumeVersionRepository extends JpaRepository<ResumeVersion, UUID> {

    List<ResumeVersion> findByResumeIdAndUserIdOrderByCreatedAtDesc(UUID resumeId, UUID userId);

    Optional<ResumeVersion> findByIdAndUserId(UUID id, UUID userId);

    Optional<ResumeVersion> findFirstByResumeIdAndUserIdOrderByCreatedAtAsc(UUID resumeId, UUID userId);
}
