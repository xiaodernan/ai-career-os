package com.careeros.resume.repository;

import com.careeros.resume.entity.Skill;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface SkillRepository extends JpaRepository<Skill, UUID> {

    Optional<Skill> findByUserIdAndNameNorm(UUID userId, String nameNorm);

    List<Skill> findByUserIdOrderByEvidenceCountDesc(UUID userId);
}
