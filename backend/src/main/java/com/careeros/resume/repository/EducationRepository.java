package com.careeros.resume.repository;

import com.careeros.resume.entity.Education;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface EducationRepository extends JpaRepository<Education, UUID> {

    List<Education> findByResumeVersionIdOrderByOrdinalAsc(UUID resumeVersionId);

    void deleteByResumeVersionId(UUID resumeVersionId);
}
