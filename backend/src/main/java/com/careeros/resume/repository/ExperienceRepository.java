package com.careeros.resume.repository;

import com.careeros.resume.entity.Experience;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ExperienceRepository extends JpaRepository<Experience, UUID> {

    List<Experience> findByResumeVersionIdOrderByOrdinalAsc(UUID resumeVersionId);

    void deleteByResumeVersionId(UUID resumeVersionId);
}
