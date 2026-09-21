package com.careeros.resume.repository;

import com.careeros.resume.entity.Project;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ProjectRepository extends JpaRepository<Project, UUID> {

    List<Project> findByResumeVersionIdOrderByOrdinalAsc(UUID resumeVersionId);

    void deleteByResumeVersionId(UUID resumeVersionId);
}
