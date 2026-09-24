package com.careeros.job.repository;

import com.careeros.common.LikePattern;
import com.careeros.common.Paging;
import com.careeros.common.Times;
import com.careeros.job.dto.JobDtos.JobListItem;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import jakarta.persistence.EntityManager;
import jakarta.persistence.Query;
import org.springframework.stereotype.Repository;

/** Native search behind GET /api/v1/jobs: FTS (tsvector) + ILIKE + facets, list without description. */
@Repository
public class JobSearchRepository {

    public record Filters(UUID userId, String q, List<String> skills, String location, String remote,
                          String company, Integer minSalary, Integer maxSalary, String status,
                          String sort, int page, int size) {
    }

    private static final Map<String, String> ORDERINGS = Map.of(
            "posted", "j.posted_at DESC",
            "salary", "j.salary_max DESC NULLS LAST, j.posted_at DESC",
            "title", "lower(j.title) ASC",
            "match", "COALESCE(m.overall, -1) DESC, j.posted_at DESC");

    private final EntityManager em;

    public JobSearchRepository(EntityManager em) {
        this.em = em;
    }

    public List<JobListItem> search(Filters f) {
        StringBuilder sql = new StringBuilder(BASE_WHERE);
        applyWhere(f, sql);
        // ORDERINGS is an immutable Map.of; getOrDefault throws on a null key, so guard
        // before the lookup — the HTTP layer defaults a missing sort to "posted", but a
        // non-web caller may pass null, and a null must not 500 the search.
        String sortKey = f.sort() == null ? "posted" : f.sort();
        sql.append(" ORDER BY ").append(ORDERINGS.getOrDefault(sortKey, ORDERINGS.get("posted")));
        sql.append(" LIMIT :limit OFFSET :offset");
        Query query = em.createNativeQuery(sql.toString());
        bind(f, query, Paging.of(f.page(), f.size()));
        return ((List<Object[]>) query.getResultList()).stream().map(JobSearchRepository::toItem).toList();
    }

    public long count(Filters f) {
        StringBuilder sql = new StringBuilder(COUNT_WHERE);
        applyWhere(f, sql);
        Query query = em.createNativeQuery(sql.toString());
        bind(f, query, null);
        return ((Number) query.getSingleResult()).longValue();
    }

    private static final String BASE_WHERE = """
            SELECT j.id, j.title, j.company_id, c.name, j.location, j.remote_type,
                   j.employment_type, j.salary_min, j.salary_max, j.salary_currency,
                   j.experience_years, j.status, j.source, j.external_url, j.posted_at,
                   j.skills, COALESCE(m.overall, NULL), COALESCE(m.id, NULL)
              FROM jobs j
              JOIN companies c ON c.id = j.company_id
              LEFT JOIN LATERAL (
                    SELECT jm.overall, jm.id FROM job_matches jm
                     WHERE jm.job_id = j.id AND jm.user_id = :userId
                     ORDER BY jm.created_at DESC LIMIT 1) m ON TRUE
             WHERE 1=1
            """;

    private static final String COUNT_WHERE = """
            SELECT COUNT(*)
              FROM jobs j
              JOIN companies c ON c.id = j.company_id
              LEFT JOIN LATERAL (
                    SELECT jm.overall, jm.id FROM job_matches jm
                     WHERE jm.job_id = j.id AND jm.user_id = :userId
                     ORDER BY jm.created_at DESC LIMIT 1) m ON TRUE
             WHERE 1=1
            """;

    private static void applyWhere(Filters f, StringBuilder sql) {
        if (f.q() != null && !f.q().isBlank()) {
            sql.append(" AND (j.tsv @@ plainto_tsquery('simple', :q) OR j.title ILIKE :qLike"
                    + " ESCAPE '!' OR c.name ILIKE :qLike ESCAPE '!')");
        }
        if (f.location() != null && !f.location().isBlank()) {
            sql.append(" AND j.location ILIKE :locationLike ESCAPE '!'");
        }
        if (f.remote() != null && !f.remote().isBlank()) {
            sql.append(" AND j.remote_type = :remote");
        }
        if (f.company() != null && !f.company().isBlank()) {
            sql.append(" AND c.name ILIKE :companyLike ESCAPE '!'");
        }
        if (f.minSalary() != null) {
            sql.append(" AND j.salary_max >= :minSalary");
        }
        if (f.maxSalary() != null) {
            sql.append(" AND j.salary_min <= :maxSalary");
        }
        if (f.status() != null && !f.status().isBlank()) {
            sql.append(" AND j.status = :status");
        }
        if (f.skills() != null && !f.skills().isEmpty()) {
            sql.append(" AND EXISTS (SELECT 1 FROM unnest(string_to_array(:skills, ',')) sk"
                    + " WHERE j.skills @> ARRAY[sk])");
        }
    }

    /**
     * @param window the page to bind, or null for a statement that does not paginate. The
     *     guard used to read {@code limit > 0} out of the same number the URL controls, so
     *     {@code ?size=0} switched the binding off on a statement whose SQL still says
     *     {@code LIMIT :limit OFFSET :offset} — an unbound parameter, i.e. a 500. Whether a
     *     statement pages is now said by the caller, and the window itself cannot be empty.
     */
    private static void bind(Filters f, Query query, Paging.Window window) {
        query.setParameter("userId", f.userId());
        if (f.q() != null && !f.q().isBlank()) {
            query.setParameter("q", f.q());
            query.setParameter("qLike", LikePattern.contains(f.q()));
        }
        if (f.location() != null && !f.location().isBlank()) {
            // Only the escaped form reaches SQL now: a raw :location bind would be a
            // parameter the statement never references.
            query.setParameter("locationLike", LikePattern.contains(f.location()));
        }
        if (f.remote() != null && !f.remote().isBlank()) {
            query.setParameter("remote", f.remote());
        }
        if (f.company() != null && !f.company().isBlank()) {
            query.setParameter("companyLike", LikePattern.contains(f.company()));
        }
        if (f.minSalary() != null) {
            query.setParameter("minSalary", f.minSalary());
        }
        if (f.maxSalary() != null) {
            query.setParameter("maxSalary", f.maxSalary());
        }
        if (f.status() != null && !f.status().isBlank()) {
            query.setParameter("status", f.status());
        }
        if (f.skills() != null && !f.skills().isEmpty()) {
            query.setParameter("skills", String.join(",", f.skills()));
        }
        if (window != null) {
            query.setParameter("limit", window.size());
            query.setParameter("offset", window.offset());
        }
    }

    private static JobListItem toItem(Object[] row) {
        return new JobListItem(
                (UUID) row[0], (String) row[1], (UUID) row[2], (String) row[3],
                (String) row[4], (String) row[5], (String) row[6],
                row[7] == null ? null : ((Number) row[7]).intValue(),
                row[8] == null ? null : ((Number) row[8]).intValue(),
                (String) row[9],
                row[10] == null ? null : ((Number) row[10]).intValue(),
                (String) row[11], (String) row[12], (String) row[13],
                Times.offset(row[14]),
                row[15] == null ? List.<String>of()
                        : java.util.Arrays.stream((Object[]) row[15]).map(String::valueOf).toList(),
                row[16] == null ? null : ((Number) row[16]).floatValue(),
                row[17] == null ? null : (UUID) row[17]);
    }
}
