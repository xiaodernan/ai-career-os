package com.careeros.job.repository;

import com.careeros.common.LikePattern;
import com.careeros.common.Paging;
import com.careeros.common.Times;
import com.careeros.job.dto.JobDtos.JobListItem;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import jakarta.persistence.EntityManager;
import jakarta.persistence.Query;
import org.springframework.stereotype.Repository;

/**
 * Native search behind GET /api/v1/jobs: FTS (tsvector) + ILIKE + facets, list without description.
 *
 * <p>Ranking has two shapes. The default filters and orders by the caller's {@code sort}. When the
 * caller asks for {@code relevance} <em>and</em> a query vector was supplied, the statement runs
 * both retrieval passes over the same filtered rows — keyword/tsvector rank and pgvector cosine
 * distance — and fuses them by reciprocal rank, which is what the agent's {@code search_jobs} tool
 * does (ai-service {@code agents/tools.py}). The candidate set is the union of the two passes, so
 * a paraphrase with no shared keyword is still recallable; the vector pass is floored on distance,
 * so a query that shares nothing with the catalogue answers 0 rows instead of ranked noise. Without
 * a vector — no provider configured, or an AI-service outage — the same request keeps its keyword
 * meaning and merely orders by relevance rank.
 */
@Repository
public class JobSearchRepository {

    /**
     * @param embedding query vector for the hybrid pass, or null to rank keyword-only. Supplied by
     *     the service only for {@code sort=relevance} with a non-blank {@code q}.
     * @param companyId exact company scope, for the company page's role list. {@code company} beside
     *     it is the board's free-text facet — an ILIKE over the name — so the two are different
     *     questions and neither can answer the other: a facet search for "Acme" is right to include
     *     Acme Labs, and a company page showing Acme Labs' roles would be wrong.
     */
    public record Filters(UUID userId, String q, List<String> skills, String location, String remote,
                          String company, UUID companyId, Integer minSalary, Integer maxSalary,
                          String status, String sort, int page, int size, List<Double> embedding) {

        /**
         * The board's own filter set, which has no company scope. Every existing call site means
         * exactly this, and the canonical form's extra component sits between two of the same type
         * only at a position this one spells out — so this is a name for the old shape rather than a
         * default anyone can forget.
         */
        public Filters(UUID userId, String q, List<String> skills, String location, String remote,
                       String company, Integer minSalary, Integer maxSalary, String status,
                       String sort, int page, int size, List<Double> embedding) {
            this(userId, q, skills, location, remote, company, null, minSalary, maxSalary, status,
                    sort, page, size, embedding);
        }
    }

    /** Matches {@code _RRF_K} in ai-service's tools.py: one fusion constant, two callers. */
    static final int RRF_K = 60;

    /**
     * Vector-pass cap. This many nearest roles join the keyword matches to form the candidate set,
     * so a large catalogue cannot make one search rank every row by distance — while the count
     * statement reads the same set, keeping the pager's total honest.
     */
    static final int SEMANTIC_CANDIDATES = 50;

    /**
     * Cosine-distance floor for the vector pass. What it actually excludes is exact
     * orthogonality, and nothing more: a row sharing no bucket with the query scores 1.0 and is
     * dropped, but a noise tail still passes. Measured against the 66 seeded roles under the
     * offline hash provider, the nonsense query "zzzzqqqnothing" hashes to three non-zero
     * dimensions of +-0.577, so its distance to a role is one minus that role's mass on those
     * three buckets: 51 rows land on exactly 1.0 and the other 15 land between 0.9614 and 0.9736,
     * every one of them under the floor. A typo therefore does not answer 0 rows -- it answers the
     * nearest few noise rows, which is what keyword search did before recall existed, only ranked
     * by a signal that means nothing. EVALUATION.md states the same limit from the other side:
     * retrieval quality under the offline provider is not a measurement anyone should act on.
     */
    static final double SEMANTIC_DISTANCE_FLOOR = 0.98;

    /**
     * The board's orderings, each ending in the row's own id.
     *
     * <p>Every sort key here can tie: two postings share a {@code posted_at} (the seed writes whole
     * days, and a bulk import writes one transaction's clock), a salary band repeats, a title
     * repeats, two matches score the same. A paged query over a non-total order is not a
     * partition -- the row that falls between two pages is decided by whichever plan PostgreSQL
     * felt like, and the same URL can answer different rows on two visits. The trailing {@code id}
     * makes each order total without changing any visible one, because it only ever separates rows
     * the previous key called equal.
     */
    private static final Map<String, String> ORDERINGS = Map.of(
            "posted", "j.posted_at DESC, j.id ASC",
            "salary", "j.salary_max DESC NULLS LAST, j.posted_at DESC, j.id ASC",
            "title", "lower(j.title) ASC, j.id ASC",
            "match", "COALESCE(m.overall, -1) DESC, j.posted_at DESC, j.id ASC",
            "relevance", "ts_rank(j.tsv, plainto_tsquery('simple', :q)) DESC, j.posted_at DESC, j.id ASC");

    private final EntityManager em;

    public JobSearchRepository(EntityManager em) {
        this.em = em;
    }

    public List<JobListItem> search(Filters f) {
        String sql;
        if (hybrid(f)) {
            sql = hybridCtes(f) + SELECT_COLUMNS + "\n"
                    + " FROM scored\n"
                    // The fused score is a sum of two reciprocal ranks, so ties are common; the
                    // trailing id keeps the paged answer a partition of the ranked set (#229).
                    + " ORDER BY rrf DESC, posted_at DESC, id ASC\n"
                    + " LIMIT :limit OFFSET :offset\n";
        } else {
            StringBuilder statement = new StringBuilder(BASE_WHERE);
            applyWhere(f, statement);
            // ORDERINGS is an immutable Map.of; getOrDefault throws on a null key, so guard
            // before the lookup — the HTTP layer defaults a missing sort to "posted", but a
            // non-web caller may pass null, and a null must not 500 the search.
            statement.append(" ORDER BY ").append(orderingFor(f));
            statement.append(" LIMIT :limit OFFSET :offset");
            sql = statement.toString();
        }
        Query query = em.createNativeQuery(sql);
        bind(f, query, Paging.of(f.page(), f.size()));
        return ((List<Object[]>) query.getResultList()).stream().map(JobSearchRepository::toItem).toList();
    }

    public long count(Filters f) {
        String sql;
        if (hybrid(f)) {
            // The same fused set the list pages over, or the pager would promise rows the ranking
            // never reaches: keyword matches ∪ the capped vector pass.
            sql = hybridCtes(f) + "SELECT COUNT(*) FROM (SELECT id FROM scored) candidates\n";
        } else {
            StringBuilder statement = new StringBuilder(COUNT_WHERE);
            applyWhere(f, statement);
            sql = statement.toString();
        }
        Query query = em.createNativeQuery(sql);
        bind(f, query, null);
        return ((Number) query.getSingleResult()).longValue();
    }

    /** How many matching postings appeared since a moment, and when the newest one did. */
    public record MatchStats(long count, OffsetDateTime newest) {
    }

    /**
     * What an alert needs and nothing more (roadmap 29.1): the board's own predicate over one
     * criterion set, read as a count and the newest arrival. The WHERE fragment is the one
     * {@link #count} and {@link #search} build, so a saved search can never alert on a set the
     * board would not answer; the query is unpaged and needs no match score, so it skips the
     * lateral join and the ranking CTEs.
     */
    public MatchStats matchStats(Filters f, OffsetDateTime since) {
        StringBuilder statement = new StringBuilder(
                "SELECT COUNT(*), MAX(j.posted_at) FROM jobs j"
                        + " JOIN companies c ON c.id = j.company_id WHERE 1=1");
        applyWhere(f, statement);
        statement.append(" AND j.posted_at >= :postedSince");
        Query query = em.createNativeQuery(statement.toString());
        // This statement carries no match-score join, so :userId has no referent; binding it
        // would be a parameter the SQL never references -- the same 500 the other way round.
        bindFilterValues(f, query);
        query.setParameter("postedSince", since);
        Object[] row = (Object[]) query.getSingleResult();
        return new MatchStats(((Number) row[0]).longValue(), Times.offset(row[1]));
    }

    /**
     * The hybrid statement only makes sense for a relevance search that was given a vector: any
     * other sort is an explicit ordering the caller asked for, and a missing vector is the
     * keyword-only world this class answered in before vectors existed.
     */
    private static boolean hybrid(Filters f) {
        return f.embedding() != null && "relevance".equals(f.sort())
                && f.q() != null && !f.q().isBlank();
    }

    private static String orderingFor(Filters f) {
        String sortKey = f.sort() == null ? "posted" : f.sort();
        // The relevance fragment is the only one that binds :q; with no query there is nothing to
        // rank by, so it falls back exactly the way an unknown sort does.
        if ("relevance".equals(sortKey) && (f.q() == null || f.q().isBlank())) {
            sortKey = "posted";
        }
        return ORDERINGS.getOrDefault(sortKey, ORDERINGS.get("posted"));
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

    /** The lexical side of the candidate set, written once so the ranked pass and the count agree. */
    private static final String LEXICAL_MATCH =
            "tsv @@ plainto_tsquery('simple', :q) OR title ILIKE :qLike ESCAPE '!'"
                    + " OR company_name ILIKE :qLike ESCAPE '!'";

    /** The row shape {@link #toItem} hydrates, plus the two columns the passes rank on. */
    private static final String FILTERED_COLUMNS = """
                SELECT j.id, j.title, j.company_id, c.name AS company_name, j.location, j.remote_type,
                       j.employment_type, j.salary_min, j.salary_max, j.salary_currency,
                       j.experience_years, j.status, j.source, j.external_url, j.posted_at,
                       j.skills, COALESCE(m.overall, NULL) AS overall, COALESCE(m.id, NULL) AS match_id,
                       j.tsv AS tsv, j.embedding AS vec
            """;

    /**
     * Rank starts at 0 to match the tool's {@code enumerate(rows)} fusion term for term. Built from
     * plain strings, not a text block: a text block drops the space before a same-line closing
     * delimiter, which would glue {@code WHERE} to its predicate.
     *
     * <p>The window ends in {@code id} because the rank is the score: two rows that tie on rank and
     * recency would otherwise be numbered in whatever order the window visited them, so the fused
     * score of a row could change between two identical queries -- and the outer ORDER BY, however
     * total, would then be sorting by a number that is not the same number twice.
     */
    private static final String KEYWORD_RANK_SELECT =
            "SELECT id, ROW_NUMBER() OVER (ORDER BY ts_rank(tsv, plainto_tsquery('simple', :q)) DESC,\n"
            + "                               posted_at DESC, id) - 1 AS rank\n"
            + "  FROM filtered\n"
            + " WHERE " + LEXICAL_MATCH;

    /**
     * The semantic pass only ranks rows whose embedding has the same dimensionality as the
     * query vector. A CASE guard guarantees ordered evaluation: the distance operator is only
     * evaluated on compatible rows, so a provider switch (or a row written by a different
     * model) degrades gracefully to keyword-only instead of throwing a dimension-mismatch
     * error. This mirrors the agent's in-process fallback in tools.py.
     */
    private static final String SEMANTIC_RANK_SELECT =
            "SELECT id, ROW_NUMBER() OVER (ORDER BY vec <=> CAST(:vec AS vector), posted_at DESC, id) - 1 AS rank\n"
            + "  FROM filtered\n"
            + " WHERE vec IS NOT NULL\n"
            + "   AND CASE\n"
            + "       WHEN vector_dims(vec) = vector_dims(CAST(:vec AS vector))\n"
            + "       THEN vec <=> CAST(:vec AS vector)\n"
            + "       END <= " + Double.toString(SEMANTIC_DISTANCE_FLOOR) + "\n"
            + " ORDER BY vec <=> CAST(:vec AS vector), posted_at DESC, id\n"
            + " LIMIT " + SEMANTIC_CANDIDATES;

    /** The fused rows: hydration columns plus the reciprocal-rank score they are ordered by. */
    private static final String SCORED_SELECT =
            "SELECT f.id, f.title, f.company_id, f.company_name, f.location, f.remote_type,\n"
            + "       f.employment_type, f.salary_min, f.salary_max, f.salary_currency,\n"
            + "       f.experience_years, f.status, f.source, f.external_url, f.posted_at,\n"
            + "       f.skills, f.overall, f.match_id,\n"
            + "       COALESCE(1.0 / (" + RRF_K + " + k.rank), 0)\n"
            + "           + COALESCE(1.0 / (" + RRF_K + " + s.rank), 0) AS rrf\n"
            + "  FROM filtered f\n"
            + "  LEFT JOIN keyword_rank k ON k.id = f.id\n"
            + "  LEFT JOIN semantic_rank s ON s.id = f.id\n"
            + " WHERE k.id IS NOT NULL OR s.id IS NOT NULL";

    /** Columns of the fused set, in the order {@link #toItem} reads them. */
    private static final String SELECT_COLUMNS = """
                SELECT id, title, company_id, company_name, location, remote_type, employment_type,
                       salary_min, salary_max, salary_currency, experience_years, status, source,
                       external_url, posted_at, skills, overall, match_id
            """;

    /**
     * The hybrid statement's common part: the filtered row set, both ranked passes over it, and the
     * reciprocally-fused candidate set. The caller appends either the page or the count over
     * {@code scored}, so what is counted is exactly what is ranked.
     */
    private static String hybridCtes(Filters f) {
        StringBuilder facets = new StringBuilder();
        applyNonQueryFilters(f, facets);
        return "WITH filtered AS (\n"
                + FILTERED_COLUMNS + "\n"
                + "  FROM jobs j\n"
                + "  JOIN companies c ON c.id = j.company_id\n"
                + "  LEFT JOIN LATERAL (\n"
                + "        SELECT jm.overall, jm.id FROM job_matches jm\n"
                + "         WHERE jm.job_id = j.id AND jm.user_id = :userId\n"
                + "         ORDER BY jm.created_at DESC LIMIT 1) m ON TRUE\n"
                + " WHERE 1=1" + facets + "\n"
                + ")\n"
                + ", keyword_rank AS (\n" + KEYWORD_RANK_SELECT + "\n)\n"
                + ", semantic_rank AS (\n" + SEMANTIC_RANK_SELECT + "\n)\n"
                + ", scored AS (\n" + SCORED_SELECT + ")\n";
    }

    /**
     * Everything the request filters on except {@code q}: the hybrid statement owns the query's own
     * predicate (inside its keyword pass), so this fragment has to leave it out rather than
     * pre-filter the rows both ranked passes are built from.
     */
    private static void applyNonQueryFilters(Filters f, StringBuilder sql) {
        if (f.location() != null && !f.location().isBlank()) {
            sql.append(" AND j.location ILIKE :locationLike ESCAPE '!'");
        }
        if (f.remote() != null && !f.remote().isBlank()) {
            sql.append(" AND j.remote_type = :remote");
        }
        if (f.company() != null && !f.company().isBlank()) {
            sql.append(" AND c.name ILIKE :companyLike ESCAPE '!'");
        }
        if (f.companyId() != null) {
            sql.append(" AND j.company_id = :companyId");
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

    private static void applyWhere(Filters f, StringBuilder sql) {
        if (f.q() != null && !f.q().isBlank()) {
            sql.append(" AND (j.tsv @@ plainto_tsquery('simple', :q) OR j.title ILIKE :qLike"
                    + " ESCAPE '!' OR c.name ILIKE :qLike ESCAPE '!')");
        }
        applyNonQueryFilters(f, sql);
    }

    /**
     * @param window the page to bind, or null for a statement that does not paginate. The
     *     guard used to read {@code limit > 0} out of the same number the URL controls, so a
     *     {@code ?size=0} switched the binding off on a statement whose SQL still says
     *     {@code LIMIT :limit OFFSET :offset} — an unbound parameter, i.e. a 500. Whether a
     *     statement pages is now said by the caller, and the window itself cannot be empty.
     */
    private static void bind(Filters f, Query query, Paging.Window window) {
        query.setParameter("userId", f.userId());
        bindFilterValues(f, query);
        // Bound only when the hybrid statement was built: a parameter the SQL never references is
        // as wrong as the other way round, and sort=posted with a vector in hand stays keyword SQL.
        if (hybrid(f)) {
            query.setParameter("vec", vectorLiteral(f.embedding()));
        }
        if (window != null) {
            query.setParameter("limit", window.size());
            query.setParameter("offset", window.offset());
        }
    }

    /**
     * The values the WHERE fragments bind. Split from {@link #bind} because two of the
     * parameters belong to the statement's shape rather than its predicate: {@code :userId} is
     * referenced only by the match-score join, which {@link #matchStats} does without, and
     * {@code :vec} only by the hybrid ranking CTEs. A statement built from {@code applyWhere}
     * alone still binds all of these.
     */
    private static void bindFilterValues(Filters f, Query query) {
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
        if (f.companyId() != null) {
            query.setParameter("companyId", f.companyId());
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
    }

    /**
     * The pgvector text form, bound as a parameter: a vector is numbers, never SQL, and the
     * statement casts the bound text ({@code CAST(:vec AS vector)}) instead of interpolating it.
     */
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
