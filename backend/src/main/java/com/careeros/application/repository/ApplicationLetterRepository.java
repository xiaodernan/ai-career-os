package com.careeros.application.repository;

import com.careeros.application.entity.ApplicationLetter;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface ApplicationLetterRepository extends JpaRepository<ApplicationLetter, UUID> {

    List<ApplicationLetter> findByApplicationIdAndUserIdOrderByCreatedAtDescIdDesc(
            UUID applicationId, UUID userId);

    List<ApplicationLetter> findByUserIdOrderByCreatedAtDescIdDesc(UUID userId);

    Optional<ApplicationLetter> findByIdAndApplicationIdAndUserId(
            UUID id, UUID applicationId, UUID userId);

    /** How many letters this application holds for this caller; another account's rows do not count. */
    long countByApplicationIdAndUserId(UUID applicationId, UUID userId);

    /** One application's letter total; the board reads a whole page of them in a single query. */
    interface LetterTotal {
        UUID getApplicationId();

        long getTotal();
    }

    @Query("""
            select l.applicationId as applicationId, count(l) as total
            from ApplicationLetter l
            where l.userId = :userId and l.applicationId in :applicationIds
            group by l.applicationId
            """)
    List<LetterTotal> countByUserAndApplicationIds(@Param("userId") UUID userId,
                                                   @Param("applicationIds") Collection<UUID> applicationIds);
}
