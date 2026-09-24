package com.careeros.conversation.repository;

import jakarta.persistence.EntityManager;
import java.util.Collection;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Repository;

/**
 * Per-conversation aggregates behind the copilot sidebar: the last thing said and how many
 * messages it took to say it. Both live in `messages`, so a list of chats could not name its own
 * content without one read per row — two grouped queries serve a whole page.
 *
 * <p>Callers pass ids they have already resolved for one user (a page of that user's chats), so
 * these statements carry no ownership predicate of their own; handing them an unscoped id set
 * would read another user's message content.
 */
@Repository
public class ConversationDigestRepository {

    /**
     * A conversation with no messages has zero of them and nothing to preview, which are different
     * facts from the page not having aggregated this row at all ({@link #UNKNOWN}).
     */
    public record Digest(String lastMessage, Integer messageCount) {
        public static final Digest UNKNOWN = new Digest(null, null);
    }

    private static final String MESSAGE_COUNTS = """
            SELECT m.conversation_id, count(*) FROM messages m
             WHERE m.conversation_id IN (:ids)
             GROUP BY m.conversation_id
            """;

    /**
     * The newest message per conversation. `id` breaks a tie inside the same timestamp so the
     * winner is stable across pages, and only the first 200 characters leave the table: a chat
     * answer can be kilobytes of markdown and the sidebar shows one line.
     */
    private static final String LAST_MESSAGES = """
            SELECT d.conversation_id, d.content
              FROM (
                SELECT m.conversation_id,
                       left(m.content, 200) AS content,
                       row_number() OVER (PARTITION BY m.conversation_id
                                          ORDER BY m.created_at DESC, m.id DESC) AS rn
                  FROM messages m
                 WHERE m.conversation_id IN (:ids)
              ) d
             WHERE d.rn = 1
            """;

    private final EntityManager em;

    public ConversationDigestRepository(EntityManager em) {
        this.em = em;
    }

    public Map<UUID, Digest> forConversations(Collection<UUID> conversationIds) {
        Map<UUID, Digest> out = new HashMap<>();
        if (conversationIds == null || conversationIds.isEmpty()) {
            return out;
        }
        Map<UUID, Integer> counts = new HashMap<>();
        for (Object[] row : rows(MESSAGE_COUNTS, conversationIds)) {
            counts.put((UUID) row[0], ((Number) row[1]).intValue());
        }
        Map<UUID, String> last = new HashMap<>();
        for (Object[] row : rows(LAST_MESSAGES, conversationIds)) {
            if (row[1] != null) {
                last.put((UUID) row[0], String.valueOf(row[1]));
            }
        }
        for (UUID id : conversationIds) {
            out.put(id, new Digest(last.get(id), counts.getOrDefault(id, 0)));
        }
        return out;
    }

    @SuppressWarnings("unchecked")
    private List<Object[]> rows(String sql, Collection<UUID> ids) {
        jakarta.persistence.Query query = em.createNativeQuery(sql);
        query.setParameter("ids", ids);
        return (List<Object[]>) query.getResultList();
    }
}
