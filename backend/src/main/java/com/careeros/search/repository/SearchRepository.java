package com.careeros.search.repository;

import com.careeros.common.Times;
import com.careeros.search.dto.SearchDtos.ApplicationHit;
import com.careeros.search.dto.SearchDtos.CompanyHit;
import com.careeros.search.dto.SearchDtos.ConversationHit;
import com.careeros.search.dto.SearchDtos.JobHit;
import com.careeros.search.dto.SearchDtos.NoteHit;
import com.careeros.search.dto.SearchDtos.ResumeHit;
import jakarta.persistence.EntityManager;
import jakarta.persistence.Query;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Repository;

/**
 * Cross-entity global search. Every user-owned group is scoped by user id; jobs and companies are
 * shared catalog rows (no user_id in schema). ILIKE matching everywhere; jobs additionally use full
 * text search with ts_rank. Groups are capped by the caller.
 */
@Repository
public class SearchRepository {

    private final EntityManager em;

    public SearchRepository(EntityManager em) {
        this.em = em;
    }

    public List<JobHit> jobs(UUID userId, String q, int limit) {
        String sql = """
                SELECT j.id, j.title, c.name, j.location, j.remote_type, j.status
                  FROM jobs j
                  JOIN companies c ON c.id = j.company_id
                 WHERE j.tsv @@ plainto_tsquery('simple', :q)
                    OR j.title ILIKE '%'||:q||'%'
                    OR c.name ILIKE '%'||:q||'%'
                 ORDER BY ts_rank(j.tsv, plainto_tsquery('simple', :q)) DESC, j.posted_at DESC
                 LIMIT :limit
                """;
        return rows(sql, params(userId, q).set("limit", limit), (row) ->
                new JobHit((UUID) row[0], (String) row[1], (String) row[2], (String) row[3],
                        (String) row[4], (String) row[5]));
    }

    public List<CompanyHit> companies(String q, int limit) {
        String sql = """
                SELECT id, name, industry, website
                  FROM companies
                 WHERE name ILIKE '%'||:q||'%'
                    OR COALESCE(industry, '') ILIKE '%'||:q||'%'
                 ORDER BY name ASC
                 LIMIT :limit
                """;
        return rows(sql, params(null, q).set("limit", limit), (row) ->
                new CompanyHit((UUID) row[0], (String) row[1], (String) row[2], (String) row[3]));
    }

    public List<ResumeHit> resumes(UUID userId, String q, int limit) {
        String sql = """
                SELECT id, title, status, updated_at
                  FROM resumes
                 WHERE user_id = :userId AND title ILIKE '%'||:q||'%'
                 ORDER BY updated_at DESC
                 LIMIT :limit
                """;
        return rows(sql, params(userId, q).set("limit", limit), (row) ->
                new ResumeHit((UUID) row[0], (String) row[1], (String) row[2], Times.offset(row[3])));
    }

    public List<NoteHit> notes(UUID userId, String q, int limit) {
        String sql = """
                SELECT id, title, left(content, 180), updated_at
                  FROM user_notes
                 WHERE user_id = :userId
                   AND (title ILIKE '%'||:q||'%' OR content ILIKE '%'||:q||'%')
                 ORDER BY updated_at DESC
                 LIMIT :limit
                """;
        return rows(sql, params(userId, q).set("limit", limit), (row) ->
                new NoteHit((UUID) row[0], (String) row[1], (String) row[2], Times.offset(row[3])));
    }

    public List<ConversationHit> conversations(UUID userId, String q, int limit) {
        String sql = """
                SELECT cv.id, cv.title,
                       (SELECT left(m.content, 180) FROM messages m
                         WHERE m.conversation_id = cv.id AND m.content ILIKE '%'||:q||'%'
                         ORDER BY m.created_at DESC LIMIT 1),
                       cv.updated_at
                  FROM conversations cv
                 WHERE cv.user_id = :userId
                   AND (cv.title ILIKE '%'||:q||'%'
                        OR EXISTS (SELECT 1 FROM messages m
                                    WHERE m.conversation_id = cv.id AND m.content ILIKE '%'||:q||'%'))
                 ORDER BY cv.updated_at DESC
                 LIMIT :limit
                """;
        return rows(sql, params(userId, q).set("limit", limit), (row) ->
                new ConversationHit((UUID) row[0], (String) row[1], (String) row[2], Times.offset(row[3])));
    }

    public List<ApplicationHit> applications(UUID userId, String q, int limit) {
        String sql = """
                SELECT id, title, company_name, status, updated_at
                  FROM applications
                 WHERE user_id = :userId
                   AND (title ILIKE '%'||:q||'%' OR COALESCE(company_name, '') ILIKE '%'||:q||'%')
                 ORDER BY updated_at DESC
                 LIMIT :limit
                """;
        return rows(sql, params(userId, q).set("limit", limit), (row) ->
                new ApplicationHit((UUID) row[0], (String) row[1], (String) row[2], (String) row[3],
                        Times.offset(row[4])));
    }

    private Params params(UUID userId, String q) {
        return new Params(userId, q);
    }

    private <T> List<T> rows(String sql, Params p, java.util.function.Function<Object[], T> mapper) {
        Query query = em.createNativeQuery(sql);
        if (p.userId != null && sql.contains(":userId")) {
            query.setParameter("userId", p.userId);
        }
        query.setParameter("q", p.q);
        if (p.limit != null) {
            query.setParameter("limit", p.limit);
        }
        return ((List<Object[]>) query.getResultList()).stream().map(mapper).toList();
    }

    /** Mutable builder so each query can bind its own extra params (limit). */
    private static final class Params {
        private final UUID userId;
        private final String q;
        private Integer limit;

        private Params(UUID userId, String q) {
            this.userId = userId;
            this.q = q;
        }

        private Params set(String key, int value) {
            if ("limit".equals(key)) {
                this.limit = value;
            }
            return this;
        }
    }
}
