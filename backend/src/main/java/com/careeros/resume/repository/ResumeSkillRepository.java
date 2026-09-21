package com.careeros.resume.repository;

import com.careeros.resume.entity.ResumeSkill;
import com.careeros.resume.entity.ResumeSkillId;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ResumeSkillRepository extends JpaRepository<ResumeSkill, ResumeSkillId> {

    List<ResumeSkill> findByResumeVersionId(UUID resumeVersionId);

    void deleteByResumeVersionId(UUID resumeVersionId);
}
