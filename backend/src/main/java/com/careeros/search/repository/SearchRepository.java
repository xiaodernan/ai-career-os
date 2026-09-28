package com.careeros.search.repository;

import com.careeros.common.LikePattern;
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
 * text search with ts_rank. Groups are capped by the caller. When a query vector is supplied, the
 * jobs channel runs hybrid retrieval (keyword + pgvector) fused by reciprocal rank, matching the
 * jobs board and the agent's {@code search_jobs} tool.
 */
@Repository
public class SearchRepository {

    private final EntityManager em;

    public SearchRepository(EntityManager em) {
        this.em = em;
    }

    /** Fuses keyword/tsvector rank and pgvector cosine distance over one filtered row set, using
     * the same reciprocal-rank formula as {@link com.careeros.job.repository.JobSearchRepository}. */
    private static final int RRF_K = 60;
    private static final int SEMANTIC_CANDIDATES = 50;
    private static final double SEMANTIC_DISTANCE_FLOOR = 0.98;

    public List<JobHit> jobs(UUID userId, String q, int limit, List<Double> embedding) {
        String sql;
        if (embedding != null && !embedding.isEmpty()) {
            sql = hybridJobsSql();
        } else {
            sql = keywordJobsSql();
        }
        return rows(sql, params(userId, q).set("limit", limit).setEmbedding(embedding), (row) ->
                new JobHit((UUID) row[0], (String) row[1], (String) row[2], (String) row[3],
                        (String) row[4], (String) row[5]));
    }

    private static String keywordJobsSql() {
        return """
                SELECT j.id, j.title, c.name, j.location, j.remote_type, j.status
                  FROM jobs j
                  JOIN companies c ON c.id = j.company_id
                 WHERE j.tsv @@ plainto_tsquery('simple', :q)
                    OR j.title ILIKE :qLike ESCAPE '!'
                    OR c.name ILIKE :qLike ESCAPE '!'
                 ORDER BY ts_rank(j.tsv, plainto_tsquery('simple', :q)) DESC, j.posted_at DESC
                 LIMIT :limit
                """;
    }

    private static String hybridJobsSql() {
        String sql = """
                WITH filtered AS (
                    SELECT j.id, j.title, c.name AS company_name, j.location, j.remote_type, j.status,
                           j.posted_at, j.tsv, j.embedding AS vec
                         FROM jobs j
                         JOIN companies c ON c.id = j.company_id
                        WHERE 1=1
                ),
                keyword_rank AS (
                    SELECT id, ROW_NUMBER() OVER (ORDER BY ts_rank(tsv, plainto_tsquery('simple', :q)) DESC,
                                                   posted_at DESC) - 1 AS rank
                      FROM filtered
                     WHERE tsv @@ plainto_tsquery('simple', :q)
                        OR title ILIKE :qLike ESCAPE '!'
                        OR company_name ILIKE :qLike ESCAPE '!'
                ),
                semantic_rank AS (
                    SELECT id, ROW_NUMBER() OVER (ORDER BY vec <=> CAST(:vec AS vector), posted_at DESC) - 1 AS rank
                      FROM filtered
                     WHERE vec IS NOT NULL
                       -- The CASE forces ordered evaluation: the distance operator then runs only on
                       -- rows whose embedding has the query's dimensionality, so a provider switch
                       -- (or a row written by another model) degrades to keyword-only instead of
                       -- erroring the whole palette. Same rule as JobSearchRepository's own pass.
                       AND CASE
                           WHEN vector_dims(vec) = vector_dims(CAST(:vec AS vector))
                           THEN vec <=> CAST(:vec AS vector)
                           END <= {FLOOR}
                     ORDER BY vec <=> CAST(:vec AS vector), posted_at DESC
                     LIMIT {CANDIDATES}
                ),
                scored AS (
                    SELECT f.id, f.title, f.company_name, f.location, f.remote_type, f.status,
                           f.posted_at,
                           COALESCE(1.0 / ({RRF_K} + k.rank), 0)
                               + COALESCE(1.0 / ({RRF_K} + s.rank), 0) AS rrf
                      FROM filtered f
                      LEFT JOIN keyword_rank k ON k.id = f.id
                      LEFT JOIN semantic_rank s ON s.id = f.id
                     WHERE k.id IS NOT NULL OR s.id IS NOT NULL
                )
                SELECT id, title, company_name, location, remote_type, status
                  FROM scored
                 ORDER BY rrf DESC, posted_at DESC
                 LIMIT :limit
                """;
        return sql.replace("{FLOOR}", Double.toString(SEMANTIC_DISTANCE_FLOOR))
                .replace("{CANDIDATES}", Integer.toString(SEMANTIC_CANDIDATES))
                .replace("{RRF_K}", Integer.toString(RRF_K));
    }

    private static String vectorLiteral(List<Double> embedding) {
        StringBuilder literal = new StringBuilder("[");
        for (int i = 0; i < embedding.size(); i++) {
            if (i > 0) {
                literal.append(',');
            }
            literal.append(Double.toString(embedding.get(i)));
        }
        return literal.append(']').toString();
    }

    public List<CompanyHit> companies(String q, int limit) {
        String sql = """
                SELECT id, name, industry, website
                  FROM companies
                 WHERE name ILIKE :qLike ESCAPE '!'
                    OR COALESCE(industry, '') ILIKE :qLike ESCAPE '!'
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
                 WHERE user_id = :userId AND title ILIKE :qLike ESCAPE '!'
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
                   AND (title ILIKE :qLike ESCAPE '!' OR content ILIKE :qLike ESCAPE '!')
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
                         WHERE m.conversation_id = cv.id AND m.content ILIKE :qLike ESCAPE '!'
                         ORDER BY m.created_at DESC LIMIT 1),
                       cv.updated_at
                  FROM conversations cv
                 WHERE cv.user_id = :userId
                   AND (cv.title ILIKE :qLike ESCAPE '!'
                        OR EXISTS (SELECT 1 FROM messages m
                                    WHERE m.conversation_id = cv.id AND m.content ILIKE :qLike ESCAPE '!'))
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
                   AND (title ILIKE :qLike ESCAPE '!' OR COALESCE(company_name, '') ILIKE :qLike ESCAPE '!')
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
        // Each group references a different subset (:userId, and only :jobs use the tsquery
        // side), and Hibernate rejects a named bind the statement never mentions — so bind
        // exactly what the SQL contains. :q is raw text for plainto_tsquery; :qLike is the
        // same term with LIKE's wildcards escaped, so "a_b" matches itself instead of "axb".
        if (p.userId != null && references(sql, "userId")) {
            query.setParameter("userId", p.userId);
        }
        if (references(sql, "q")) {
            query.setParameter("q", p.q);
        }
        if (references(sql, "qLike")) {
            query.setParameter("qLike", LikePattern.contains(p.q));
        }
        if (p.limit != null) {
            query.setParameter("limit", p.limit);
        }
        if (p.embedding != null && references(sql, "vec")) {
            query.setParameter("vec", vectorLiteral(p.embedding));
        }
        return ((List<Object[]>) query.getResultList()).stream().map(mapper).toList();
    }

    /** True only for a whole named parameter: ':q' must not match inside ':qLike'. */
    private static boolean references(String sql, String param) {
        return java.util.regex.Pattern.compile(":" + param + "\\b").matcher(sql).find();
    }

    /** Mutable builder so each query can bind its own extra params (limit). */
    private static final class Params {
        private final UUID userId;
        private final String q;
        private Integer limit;
        private List<Double> embedding;

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

        private Params setEmbedding(List<Double> embedding) {
            this.embedding = embedding;
            return this;
        }
    }
}
