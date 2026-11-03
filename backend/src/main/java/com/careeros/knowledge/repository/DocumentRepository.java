package com.careeros.knowledge.repository;

import com.careeros.knowledge.entity.Document;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.transaction.annotation.Transactional;

public interface DocumentRepository extends JpaRepository<Document, UUID> {

    Optional<Document> findByIdAndUserId(UUID id, UUID userId);

    Optional<Document> findByFileKey(String fileKey);

    /**
     * Whether a row that retrieval can still quote names this key. Retired rows are the ones
     * the delete path left behind, so they are excluded: they keep their key as the audit
     * record, and the audit record is not a reason to hold the bytes.
     */
    boolean existsByFileKeyAndStatusNot(String fileKey, String status);

    /**
     * The keys of rows retired before {@code cutoff} that no source still names (roadmap 44.3).
     * The purge deletes those rows, and a row's chunks and its object go with it -- so the rows
     * that a source pointer keeps out of the delete keep their key as 44.2's recovery trail, and
     * naming them here is what makes the sweep's own counting agree with what it removes.
     */
    @Query("""
            select d.fileKey from Document d
            where d.status = :status and d.updatedAt < :cutoff and d.fileKey is not null
              and not exists (select 1 from KnowledgeSource s where s.documentId = d.id)
            """)
    List<String> findRetiredFileKeysBefore(@Param("status") String status,
                                           @Param("cutoff") OffsetDateTime cutoff);

    /**
     * How many chunks belong to rows retired before {@code cutoff} that no source still names.
     * The database removes them with the document row through
     * {@code document_chunks.document_id ... on delete cascade}, so this is the only place their
     * number is ever read -- and it has to be read before the delete, because afterwards there
     * is nothing left to count.
     */
    @Query(value = """
            select count(*) from document_chunks c
            where c.document_id in (select d.id from documents d
                                    where d.status = :status and d.updated_at < :cutoff
                                      and not exists (select 1 from knowledge_sources s
                                                      where s.document_id = d.id))
            """, nativeQuery = true)
    long countRetiredChunksBefore(@Param("status") String status,
                                  @Param("cutoff") OffsetDateTime cutoff);

    /**
     * How many rows are retired and past the window but still named by a source. Normally none:
     * the delete path drops the source in the same transaction that retires the copy. A non-zero
     * answer is a row the purge deliberately skipped, because taking a document a live source
     * points at would break that source's own delete for the sake of a row nobody reads.
     */
    @Query("""
            select count(d) from Document d
            where d.status = :status and d.updatedAt < :cutoff
              and exists (select 1 from KnowledgeSource s where s.documentId = d.id)
            """)
    long countRetiredButStillNamedBefore(@Param("status") String status,
                                         @Param("cutoff") OffsetDateTime cutoff);

    /**
     * Delete the rows retired before {@code cutoff} that no source still names. Its own
     * transaction, like the credential deletes: the sweep's content phase must not hold the
     * token tables' work, and the chunks go with the row in the same statement.
     */
    @Modifying
    @Transactional
    @Query("""
            delete from Document d
            where d.status = :status and d.updatedAt < :cutoff
              and not exists (select 1 from KnowledgeSource s where s.documentId = d.id)
            """)
    int deleteRetiredBefore(@Param("status") String status, @Param("cutoff") OffsetDateTime cutoff);

    /**
     * Every key any document row names, in every status (roadmap 48.2). Retired rows are included
     * here although 44.2's reference check excludes them, because the two questions differ: the
     * delete path asks whether the bytes are still useful, and the bucket sweep asks whether any
     * row still claims them. A retired row claims its key until 44.3 purges the row, and the
     * purge hands the key to the reclaimer as it goes -- so the only object this read cannot
     * account for is one no row ever named.
     */
    @Query("select d.fileKey from Document d where d.fileKey is not null")
    List<String> findAllFileKeys();

    List<Document> findBySourceId(UUID sourceId);

    List<Document> findByUserId(UUID userId);
}
