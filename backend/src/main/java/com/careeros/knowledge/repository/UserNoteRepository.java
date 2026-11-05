package com.careeros.knowledge.repository;

import com.careeros.knowledge.entity.UserNote;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface UserNoteRepository extends JpaRepository<UserNote, UUID> {

    Page<UserNote> findByUserIdOrderByUpdatedAtDescIdAsc(UUID userId, Pageable pageable);

    /**
     * 64.2: the notes carrying one tag, newest first. `tags` is a Postgres
     * {@code text[]} column -- not an element collection Hibernate can walk in
     * JPQL -- so the membership test is SQL's own {@code = ANY(tags)}. The cast
     * is explicit because the bound parameter arrives as varchar and Postgres
     * will not compare varchar to text without it.
     */
    @Query(value = """
            select * from user_notes
            where user_id = :userId and cast(:tag as text) = any(tags)
            order by updated_at desc, id asc
            """, countQuery = """
            select count(*) from user_notes
            where user_id = :userId and cast(:tag as text) = any(tags)
            """, nativeQuery = true)
    Page<UserNote> findByTag(@Param("userId") UUID userId, @Param("tag") String tag,
                             Pageable pageable);

    Optional<UserNote> findByIdAndUserId(UUID id, UUID userId);

    List<UserNote> findByUserId(UUID userId);
}
