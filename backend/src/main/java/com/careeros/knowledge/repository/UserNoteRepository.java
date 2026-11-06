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

    /**
     * 69.2: how many notes carry each tag, so the filter row can say what is
     * behind a tag before the reader spends a click on it.
     *
     * <p>The count is over the unnested array, for the same reason the filter
     * above is `= any(tags)`: `tags` is a Postgres `text[]` column and Hibernate
     * has no JPQL element collection to walk. A note with no tags contributes no
     * rows, so an untagged note is in the list's total but in no tag's count --
     * which is the honest answer, since no tag would find it.
     */
    @Query(value = """
            select tag, count(*) as total
            from (select unnest(tags) as tag from user_notes where user_id = :userId) unnested
            group by tag
            order by count(*) desc, tag asc
            """, nativeQuery = true)
    List<TagCount> countByTag(@Param("userId") UUID userId);

    /** One row of `countByTag`: a label the reader typed and how many notes carry it. */
    interface TagCount {
        String getTag();

        long getTotal();
    }

    Optional<UserNote> findByIdAndUserId(UUID id, UUID userId);

    List<UserNote> findByUserId(UUID userId);
}
