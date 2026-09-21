package com.careeros.resume.repository;

import com.careeros.resume.entity.Achievement;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface AchievementRepository extends JpaRepository<Achievement, UUID> {

    List<Achievement> findByResumeVersionIdOrderByOrdinalAsc(UUID resumeVersionId);

    void deleteByResumeVersionId(UUID resumeVersionId);
}
