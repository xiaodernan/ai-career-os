package com.careeros.application.repository;

import com.careeros.application.entity.ApplicationLetter;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ApplicationLetterRepository extends JpaRepository<ApplicationLetter, UUID> {

    List<ApplicationLetter> findByApplicationIdAndUserIdOrderByCreatedAtDescIdDesc(
            UUID applicationId, UUID userId);

    List<ApplicationLetter> findByUserIdOrderByCreatedAtDescIdDesc(UUID userId);
}
