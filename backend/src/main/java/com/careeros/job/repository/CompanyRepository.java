package com.careeros.job.repository;

import com.careeros.job.entity.Company;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface CompanyRepository extends JpaRepository<Company, UUID> {

    Optional<Company> findByName(String name);

    Page<Company> findByNameContainingIgnoreCase(String q, Pageable pageable);

    @Query("SELECT c.id, COUNT(j.id) FROM Company c LEFT JOIN Job j ON j.companyId = c.id "
            + "AND j.status = 'open' GROUP BY c.id")
    List<Object[]> openRoleCounts();

    @Query("SELECT COUNT(j.id) FROM Job j WHERE j.companyId = :companyId AND j.status = 'open'")
    long countOpenRoles(@Param("companyId") UUID companyId);
}
