package com.careeros.inbound.repository;

import com.careeros.inbound.entity.InboundMail;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

public interface InboundMailRepository extends JpaRepository<InboundMail, UUID> {

    Optional<InboundMail> findByUserIdAndMessageKey(UUID userId, String messageKey);

    Optional<InboundMail> findByIdAndUserId(UUID id, UUID userId);

    /** The replies page: one account's letters newest first. */
    Page<InboundMail> findByUserIdOrderByReceivedAtDescIdDesc(UUID userId, Pageable pageable);

    /**
     * The replies page with a search (roadmap 47.1): the same ordering, narrowed to the letters
     * whose subject, sender, company or role contains `q`, case aside.
     *
     * `LOCATE` rather than `LIKE` on purpose: a reader who types `%` into a search box is
     * looking for a percent sign, not asking for every letter, and a bound `LIKE` pattern
     * would quietly treat their words as wildcards. The four `COALESCE`s keep a letter with
     * no company or role searchable by the fields it does have, because a null operand in
     * `OR` must not swallow the other matches.
     */
    @Query("""
            SELECT m FROM InboundMail m
             WHERE m.userId = :userId
               AND (LOCATE(:q, LOWER(COALESCE(m.subject, ''))) > 0
                    OR LOCATE(:q, LOWER(COALESCE(m.fromAddress, ''))) > 0
                    OR LOCATE(:q, LOWER(COALESCE(m.company, ''))) > 0
                    OR LOCATE(:q, LOWER(COALESCE(m.role, ''))) > 0)
             ORDER BY m.receivedAt DESC, m.id DESC
            """)
    Page<InboundMail> search(UUID userId, String q, Pageable pageable);

    /** What the inbox may carry (37.3): the letters already filed on an application. */
    List<InboundMail> findByUserIdAndApplicationIdIsNotNullOrderByReceivedAtDescIdDesc(
            UUID userId, Pageable pageable);
}
