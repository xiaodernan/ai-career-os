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
     * The replies page with its two filters (roadmap 49.1-49.2): the same ordering, narrowed
     * to the letters whose subject, sender, company, role or own text contains `q` (case
     * aside) and to the reading `intent` -- or, when `unread` is true, to the letters no
     * reading has answered yet.
     *
     * The body is searched because the words a reader remembers are usually in the letter
     * itself ("we would like to schedule"), not in its subject line; an envelope-only search
     * would answer that memory with an empty page. A blank `q` is still no filter rather than
     * an empty room: the first branch asks the literal empty string, which every row
     * satisfies, so the LOCATE below is never the reason a page came back empty. `LOCATE`
     * rather than `LIKE` on purpose: a reader who types `%` into a search box is looking for
     * a percent sign, not asking for every letter, and a bound `LIKE` pattern would quietly
     * treat their words as wildcards. The five `COALESCE`s keep a letter with no company,
     * role or body searchable by the fields it does have, because a null operand in `OR` must
     * not swallow the other matches.
     */
    @Query("""
            SELECT m FROM InboundMail m
             WHERE m.userId = :userId
               AND (:q = ''
                    OR LOCATE(:q, LOWER(COALESCE(m.subject, ''))) > 0
                    OR LOCATE(:q, LOWER(COALESCE(m.fromAddress, ''))) > 0
                    OR LOCATE(:q, LOWER(COALESCE(m.company, ''))) > 0
                    OR LOCATE(:q, LOWER(COALESCE(m.role, ''))) > 0
                    OR LOCATE(:q, LOWER(COALESCE(m.bodyText, ''))) > 0)
               AND (:intent IS NULL OR m.intent = :intent)
               AND (:unread = FALSE OR m.intent IS NULL)
             ORDER BY m.receivedAt DESC, m.id DESC
            """)
    Page<InboundMail> findPage(UUID userId, String q, String intent, boolean unread, Pageable pageable);

    /**
     * What the chips above the list would show (roadmap 49.4): one count per reading, under the
     * same words as the page -- the reading filter deliberately does not apply here, because
     * the chips count their alternatives rather than the one already picked.
     *
     * <p>The search half mirrors {@link #findPage}: the same five fields, the same empty-string
     * escape for a blank box, so the number on a chip and the page it opens are answers to the
     * same question. A null intent (a letter no reading has answered) comes back as a null key;
     * the service names it `unread`.
     */
    @Query("""
            SELECT m.intent, COUNT(m) FROM InboundMail m
             WHERE m.userId = :userId
               AND (:q = ''
                    OR LOCATE(:q, LOWER(COALESCE(m.subject, ''))) > 0
                    OR LOCATE(:q, LOWER(COALESCE(m.fromAddress, ''))) > 0
                    OR LOCATE(:q, LOWER(COALESCE(m.company, ''))) > 0
                    OR LOCATE(:q, LOWER(COALESCE(m.role, ''))) > 0
                    OR LOCATE(:q, LOWER(COALESCE(m.bodyText, ''))) > 0)
             GROUP BY m.intent
            """)
    List<Object[]> countByIntent(UUID userId, String q);

    /** What the inbox may carry (37.3): the letters already filed on an application. */
    List<InboundMail> findByUserIdAndApplicationIdIsNotNullOrderByReceivedAtDescIdDesc(
            UUID userId, Pageable pageable);
}
