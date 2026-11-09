package com.careeros.network.repository;

import com.careeros.network.entity.Contact;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

/**
 * The registry's reads: the page's own question, most recently touched first (the order the
 * page renders and the order "who have I not talked to" asks about), the whole registry for the
 * bundle, and the user-scoped single find every mutation is anchored on.
 */
public interface ContactRepository extends JpaRepository<Contact, UUID> {

    /**
     * One user's people, narrowed by whatever the box holds (70.3) and by the relation
     * the chip row chose (80). A blank needle asks nothing, so an untyped box is the
     * whole registry rather than a search for the empty string, and the word is asked
     * with {@code LOCATE} rather than a derived containment keyword because the reader's
     * characters are data: a person whose name really carries an underscore is found by
     * spelling it, and a box of {@code %} is one character rather than every row. The
     * relation clause binds the same empty-means-no-constraint shape, so a reader who
     * never taps a chip keeps the whole registry, not an empty one.
     */
    String BOARD_WHERE = """
             WHERE c.userId = :userId
               AND (:needle = ''
                    OR LOCATE(:needle, LOWER(c.name)) > 0
                    OR LOCATE(:needle, LOWER(COALESCE(c.role, ''))) > 0
                    OR LOCATE(:needle, LOWER(COALESCE(c.company, ''))) > 0
                    OR LOCATE(:needle, LOWER(COALESCE(c.relation, ''))) > 0
                    OR LOCATE(:needle, LOWER(COALESCE(c.email, ''))) > 0
                    OR LOCATE(:needle, LOWER(COALESCE(c.notes, ''))) > 0)
               AND (:relation = ''
                    OR LOWER(COALESCE(c.relation, '')) = :relation)
            """;

    /**
     * The registry as the page asks it (72.1). The tiebreaker is the row's own id, so two people
     * touched in the same instant keep one order across pages rather than trading places on every
     * read. The count query repeats the same {@code BOARD_WHERE} -- and only that clause -- so
     * {@code total} counts the people who spell the word and sit behind the chip, not the whole
     * registry: a pager that offered two pages of everybody while the board showed one page of
     * matches would be answering a different question from the box above it.
     */
    @Query(value = "SELECT c FROM Contact c" + BOARD_WHERE + " ORDER BY c.updatedAt DESC, c.id ASC",
            countQuery = "SELECT COUNT(c) FROM Contact c" + BOARD_WHERE)
    Page<Contact> findBoard(@Param("userId") UUID userId, @Param("needle") String needle,
            @Param("relation") String relation, Pageable pageable);

    /**
     * The chip row's own question (80): which relations the reader's registry actually holds, and
     * how many rows sit behind each. Only the reader's rows, only non-blank relation values, in
     * count order so the most-used chip leads. A native statement: the table is the vocabulary
     * and the columns, not the entity, and the reader does not deserve a page object wrapped
     * around a count.
     */
    @Query(value = """
             SELECT relation, COUNT(*) FROM contacts
              WHERE user_id = :userId AND relation IS NOT NULL AND relation <> ''
              GROUP BY relation ORDER BY COUNT(*) DESC, relation ASC
            """, nativeQuery = true)
    List<Object[]> relationCounts(@Param("userId") UUID userId);

    /**
     * Every row the account owns, which is what the export bundle carries (roadmap 40.3): a bundle
     * has no box to answer, so it asks for the registry rather than a search of it.
     */
    List<Contact> findByUserIdOrderByUpdatedAtDesc(UUID userId);

    /**
     * Epic 81: the caller's people, most recently touched first, ties broken by id, paged by the cap.
     */
    Page<Contact> findByUserIdOrderByUpdatedAtDescIdAsc(UUID userId, Pageable pageable);

    Optional<Contact> findByIdAndUserId(UUID id, UUID userId);
}
