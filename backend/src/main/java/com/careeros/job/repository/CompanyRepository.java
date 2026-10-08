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

    /**
     * The company board's two list queries, both ordered by name.
     *
     * <p>A paged list is only a partition of its catalog if the order is part of the query
     * rather than a property of the database's mood: {@code findAll(pageable)} asked
     * PostgreSQL for rows in whatever order it liked, so two requests for the same page could
     * answer different rows and a row could be skipped by one page and served by the next.
     * The name is the column the board sorts by visually and the schema declares unique, so
     * ordering by it is total -- the tie-break nobody needs.
     */
    Page<Company> findAllByOrderByNameAsc(Pageable pageable);

    Page<Company> findByNameContainingIgnoreCaseOrderByNameAsc(String q, Pageable pageable);

    @Query("SELECT c.id, COUNT(j.id) FROM Company c LEFT JOIN Job j ON j.companyId = c.id "
            + "AND j.status = 'open' GROUP BY c.id")
    List<Object[]> openRoleCounts();

    @Query("SELECT COUNT(j.id) FROM Job j WHERE j.companyId = :companyId AND j.status = 'open'")
    long countOpenRoles(@Param("companyId") UUID companyId);
}
