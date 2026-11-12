package com.careeros.application.repository;

import com.careeros.application.entity.Application;
import java.time.OffsetDateTime;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface ApplicationRepository extends JpaRepository<Application, UUID> {

    /**
     * The card's own words, in the one spelling a reader's characters survive (70.1).
     *
     * <p>The board's list used to be four derived methods that differed only by which filter happened
     * to be set, and a fifth filter would have meant eight. A reader's word is not a filter of that
     * kind either: like the company board (58.1) and the reply inbox (49.1), the needle arrives already
     * trimmed and lower-cased from the service and is asked with {@code LOCATE}, which has no pattern
     * language to misunderstand a {@code %} or an underscore with. The three nullable columns are
     * {@code COALESCE}d because a card with no note is still a card the reader may be looking for.
     */
    String BOARD_WHERE = """
             WHERE a.userId = :userId
               AND (:status = '' OR a.status = :status)
               AND (:jobId IS NULL OR a.jobId = :jobId)
               AND (:needle = ''
                    OR LOCATE(:needle, LOWER(a.title)) > 0
                    OR LOCATE(:needle, LOWER(COALESCE(a.companyName, ''))) > 0
                    OR LOCATE(:needle, LOWER(COALESCE(a.notes, ''))) > 0)
            """;

    Optional<Application> findByIdAndUserId(UUID id, UUID userId);

    /**
     * The board's own read, and the reason it is not a derived query.
     *
     * <p>The order is part of the question: a page is only a partition of this pipeline if two requests
     * for the same window answer the same rows, so {@code id} breaks every tie the timestamp leaves.
     */
    @Query("SELECT a FROM Application a" + BOARD_WHERE + " ORDER BY a.updatedAt DESC, a.id ASC")
    Page<Application> findPage(@Param("userId") UUID userId, @Param("status") String status,
            @Param("jobId") UUID jobId, @Param("needle") String needle, Pageable pageable);

    /**
     * One column of the board, in the order the reader arranged it (70.1).
     *
     * <p>{@code status} is a requirement here rather than a choice: asking for a column by name is what
     * makes {@code position} a total order to page over, and the same needle narrows inside it.
     */
    @Query("SELECT a FROM Application a" + BOARD_WHERE + " ORDER BY a.position ASC, a.id ASC")
    Page<Application> findColumnPage(@Param("userId") UUID userId, @Param("status") String status,
            @Param("jobId") UUID jobId, @Param("needle") String needle, Pageable pageable);

    /**
     * The whole pipeline, newest first, with nothing narrowed away. The board asks its filters through
     * {@link #findPage}; this one belongs to the readers that take every row they have -- the weekly
     * letter's funnel and the bundle's `applications` section.
     */
    Page<Application> findByUserIdOrderByUpdatedAtDescIdAsc(UUID userId, Pageable pageable);

    List<Application> findByUserIdAndJobId(UUID userId, UUID jobId);

    /**
     * The cards a page of rehearsals names (57.4) -- one read for the whole
     * page, so the stage badge costs the list one query rather than one per row.
     */
    List<Application> findByUserIdAndIdIn(UUID userId, Collection<UUID> ids);

    /**
     * The cards a reply's employer names (roadmap 37.3), case aside and nothing else: a match
     * that is not the same name is a guess, and a guess that files a reply on the wrong card is
     * worse than a reply waiting for the reader. The service narrows a repeated name by role.
     */
    List<Application> findByUserIdAndCompanyNameIgnoreCase(UUID userId, String companyName);

    /**
     * The rows the calendar feed speaks for (roadmap 34), in the order a day lists them: a row
     * with no {@code reminder_at} is not a time the reader ever wrote down, so it has no event.
     */
    List<Application> findByUserIdAndReminderAtIsNotNullOrderByReminderAtAscIdAsc(UUID userId);

    /**
     * The accounts whose reminder came due inside the ticker's window (roadmap 35.1). Closed
     * applications are excluded for the dashboard's own reason: `offer` and `rejected` are
     * decisions already made, and a clock that rings for them would wake the reader about work
     * that is finished.
     */
    @Query("SELECT DISTINCT a.userId FROM Application a WHERE a.reminderAt > :since "
            + "AND a.reminderAt <= :until AND a.status NOT IN ('offer', 'rejected')")
    List<UUID> findUserIdsWithReminderBetween(@Param("since") OffsetDateTime since,
            @Param("until") OffsetDateTime until);

    long countByUserId(UUID userId);

    long countByUserIdAndStatus(UUID userId, String status);

    @Query("SELECT a.status, COUNT(a) FROM Application a WHERE a.userId = :userId GROUP BY a.status")
    List<Object[]> statusCounts(@Param("userId") UUID userId);

    /**
     * Every account with at least one application -- the weekly letter's audience (19.4). A
     * user with no applications has nothing a week can say; their first letter arrives once
     * they have something to report.
     */
    @Query("SELECT DISTINCT a.userId FROM Application a")
    List<UUID> distinctUserIds();
}
