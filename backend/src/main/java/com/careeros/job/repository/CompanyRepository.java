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

    /**
     * The board's searched branch, and the reason it is not a derived query (58.1).
     *
     * <p>What a reader types into a search box is data, and the spelling this method replaces treated
     * it as a pattern: {@code findByNameContainingIgnoreCaseOrderByNameAsc} wrapped the value in
     * {@code %…%} without escaping it, so {@code ?q=%} answered the whole catalog, {@code ?q=a_b}
     * matched a company named "axb", and a name that genuinely carries an underscore could not be
     * asked for by its own characters. That is the failure {@code common/LikePattern} exists to stop,
     * arriving on the one list that had never been through it.
     *
     * <p>{@code LOCATE} asks the containment question without a pattern language at all, which is how
     * {@code InboundMailRepository.findPage} answers the same one; the needle arrives already trimmed
     * and lower-cased from the service, and the order stays part of the query because a page is only a
     * partition of this catalog if it is.
     */
    @Query("""
            SELECT c FROM Company c
             WHERE LOCATE(:needle, LOWER(c.name)) > 0
             ORDER BY c.name ASC
            """)
    Page<Company> searchByName(@Param("needle") String needle, Pageable pageable);

    @Query("SELECT c.id, COUNT(j.id) FROM Company c LEFT JOIN Job j ON j.companyId = c.id "
            + "AND j.status = 'open' GROUP BY c.id")
    List<Object[]> openRoleCounts();

    @Query("SELECT COUNT(j.id) FROM Job j WHERE j.companyId = :companyId AND j.status = 'open'")
    long countOpenRoles(@Param("companyId") UUID companyId);
}
