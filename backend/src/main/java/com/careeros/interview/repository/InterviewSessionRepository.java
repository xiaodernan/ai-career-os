package com.careeros.interview.repository;

import com.careeros.interview.entity.InterviewSession;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface InterviewSessionRepository extends JpaRepository<InterviewSession, UUID> {

    /**
     * The rehearsal's own words, in the spelling a reader's characters survive (70.4).
     *
     * <p>The list was two derived methods that differed only by whether a card id had been set --
     * the drawer's rehearsals (57.1) and the whole history -- and a reader's word would have made
     * them four. Like the pipeline (70.1) and the registry (70.3), the needle arrives already
     * trimmed and lower-cased from the service and is asked with {@code LOCATE}, which has no
     * pattern language to read a {@code %} or an underscore as anything but characters. The two
     * columns a rehearsal may leave empty are {@code COALESCE}d, because a session started without
     * a company is still a session the reader may be looking for.
     *
     * <p>The search reads the session's own columns, not the turns it contains: a rehearsal is one
     * row on this board, and a join into its questions would answer the same row once per question.
     */
    String BOARD_WHERE = """
             WHERE s.userId = :userId
               AND (:applicationId IS NULL OR s.applicationId = :applicationId)
               AND (:needle = ''
                    OR LOCATE(:needle, LOWER(COALESCE(s.companyName, ''))) > 0
                    OR LOCATE(:needle, LOWER(COALESCE(s.positionTitle, ''))) > 0
                    OR LOCATE(:needle, LOWER(s.mode)) > 0)
            """;

    /**
     * The board's own read, newest first, with nothing narrowed away unless it was asked for.
     *
     * <p>{@code id} breaks every tie the start timestamp leaves: two rehearsals begun in the same
     * instant still have to land on the same side of a page boundary on every request.
     */
    @Query("SELECT s FROM InterviewSession s" + BOARD_WHERE
            + " ORDER BY s.startedAt DESC, s.id ASC")
    Page<InterviewSession> findPage(@Param("userId") UUID userId,
            @Param("applicationId") UUID applicationId, @Param("needle") String needle,
            Pageable pageable);

    Optional<InterviewSession> findByIdAndUserId(UUID id, UUID userId);

    long countByUserId(UUID userId);

    /** One card's rehearsals (57.2): the packet's fifth row is this number. */
    long countByApplicationIdAndUserId(UUID applicationId, UUID userId);
}
