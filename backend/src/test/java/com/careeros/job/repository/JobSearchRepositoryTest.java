package com.careeros.job.repository;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.job.repository.JobSearchRepository.Filters;
import com.careeros.job.repository.JobSearchRepository.MatchStats;
import com.careeros.job.repository.JobSearchRepository.SavedBoard;
import jakarta.persistence.EntityManager;
import jakarta.persistence.Query;
import java.time.OffsetDateTime;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

/**
 * Guardrails for the native job-search SQL (plain Mockito — no DB, no Spring context):
 * (1) the user-controlled ORDER BY goes through a strict allowlist, so a malicious
 *     {@code sort} can never be interpolated into the statement; (2) every named parameter
 *     referenced by the WHERE fragments is actually bound, and nothing is bound that the
 *     SQL does not reference. That binding symmetry is what keeps a future filter addition
 *     from silently 500-ing on "parameter not bound" — the only other coverage is the
 *     Docker-only integration test; (3) the paging window taken off the URL is made safe
 *     before it is spliced into {@code LIMIT}/{@code OFFSET}; (4) every ORDER BY ends in
 *     the row's own id, so a page is a partition of the catalogue rather than of a plan's mood.
 */
class JobSearchRepositoryTest {

    private final UUID userId = UUID.randomUUID();
    private EntityManager em;
    private Query query;
    private JobSearchRepository repo;
    private Set<String> bound;
    private Map<String, Object> params;

    @BeforeEach
    void setUp() {
        em = mock(EntityManager.class);
        query = mock(Query.class);
        repo = new JobSearchRepository(em);
        bound = new HashSet<>();
        params = new LinkedHashMap<>();
        when(em.createNativeQuery(anyString())).thenReturn(query);
        doAnswer(inv -> {
            bound.add(inv.getArgument(0));
            params.put(inv.getArgument(0), inv.getArgument(1));
            return query;
        }).when(query).setParameter(anyString(), any());
        when(query.getResultList()).thenReturn(List.of());
        when(query.getSingleResult()).thenReturn(0L);
    }

    private String capturedSql() {
        ArgumentCaptor<String> cap = ArgumentCaptor.forClass(String.class);
        verify(em).createNativeQuery(cap.capture());
        return cap.getValue();
    }

    private static Set<String> placeholders(String sql) {
        Set<String> names = new HashSet<>();
        Matcher m = Pattern.compile(":(\\w+)").matcher(sql);
        while (m.find()) {
            names.add(m.group(1));
        }
        return names;
    }

    /**
     * The outer ORDER BY of a captured statement, without the paging clause that may follow it.
     * The statement also carries inner ones -- the LATERAL lateral join orders by {@code created_at
     * DESC LIMIT 1} to pick the latest match -- so this is the last, not the first.
     */
    private static String orderByClause(String sql) {
        int at = sql.lastIndexOf("ORDER BY ");
        assertThat(at).isGreaterThanOrEqualTo(0);
        String rest = sql.substring(at + "ORDER BY ".length());
        int limit = rest.indexOf(" LIMIT");
        return (limit < 0 ? rest : rest.substring(0, limit)).trim();
    }

    private Filters fullFilters(String sort) {
        return new Filters(userId, "java", List.of("spring", "kafka"), "Remote", "remote",
                "Acme", 100, 200, "open", sort, 2, 25, null);
    }

    /** Sparse filters, so the only bound parameters besides userId are the paging ones. */
    private Filters paged(int page, int size) {
        return new Filters(userId, null, null, null, null, null, null, null, null, null,
                page, size, null);
    }

    /** A relevance search that was handed a vector — the shape that switches on the hybrid SQL. */
    private Filters hybrid(String sort) {
        return new Filters(userId, "java", null, null, null, null, null, null, null,
                sort, 0, 20, List.of(0.25, -0.5));
    }

    @Test
    void searchBindsExactlyTheParametersItsSqlReferences() {
        repo.search(fullFilters("salary"));
        assertThat(placeholders(capturedSql())).isEqualTo(bound);
    }

    @Test
    void countBindsExactlyTheParametersItsSqlReferences() {
        repo.count(fullFilters("posted"));
        assertThat(placeholders(capturedSql())).isEqualTo(bound);
    }

    /**
     * The alert statement is built from the same WHERE fragment but skips the match-score
     * join, so it is the one statement in this class whose SQL never says {@code :userId} —
     * and binding it anyway made every inbox read a 500 (found by SavedSearchAlertIT).
     */
    @Test
    void theAlertStatsBindExactlyTheParametersItsSqlReferencesAndNeverTheUserId() {
        OffsetDateTime since = OffsetDateTime.parse("2026-10-01T00:00:00Z");
        OffsetDateTime newest = OffsetDateTime.parse("2026-10-28T09:30:00Z");
        when(query.getSingleResult()).thenReturn(new Object[] {3L, newest});

        MatchStats stats = repo.matchStats(fullFilters("posted"), since);

        String sql = capturedSql();
        assertThat(placeholders(sql)).isEqualTo(bound);
        assertThat(bound).doesNotContain("userId");
        assertThat(params).containsEntry("postedSince", since);
        assertThat(stats.count()).isEqualTo(3);
        assertThat(stats.newest()).isEqualTo(newest);
    }

    @Test
    void sparseFiltersBindNoUnusedParameters() {
        Filters f = new Filters(userId, null, null, null, null, null, null, null, null,
                null, 0, 10, null);
        repo.search(f);
        String sql = capturedSql();
        assertThat(placeholders(sql)).isEqualTo(bound);
        // only userId + pagination are in play; no filter placeholders leak in
        assertThat(bound).containsExactlyInAnyOrder("userId", "limit", "offset");
    }

    @Test
    void unknownSortFallsBackToPostedAndIsNeverInterpolated() {
        repo.search(fullFilters("salary; DROP TABLE jobs;--"));
        String sql = capturedSql();
        assertThat(sql).contains("ORDER BY j.posted_at DESC");
        assertThat(sql).doesNotContain("DROP TABLE");
        assertThat(sql).doesNotContain("salary;");
    }

    @Test
    void eachAllowedSortMapsToItsOwnFragment() {
        repo.search(fullFilters("match"));
        assertThat(capturedSql()).contains("ORDER BY COALESCE(m.overall, -1) DESC");
    }

    @Test
    void nullSortFallsBackToPostedWithoutNpe() {
        // Regression: Map.of().getOrDefault(null,..) throws; search() must tolerate a
        // null sort (only the HTTP layer guarantees a default, the repository can't).
        repo.search(fullFilters(null));
        assertThat(capturedSql()).contains("ORDER BY j.posted_at DESC");
    }

    @Test
    void countQueryCarriesNoPaginationClause() {
        repo.count(fullFilters("title"));
        // the LATERAL subquery legitimately contains "LIMIT 1"; what must be absent is
        // the *pagination* :limit/:offset the list query appends.
        String sql = capturedSql();
        assertThat(sql).doesNotContain(":limit").doesNotContain(":offset");
        assertThat(bound).doesNotContain("limit", "offset");
    }

    @Test
    void everyLikeFilterBindsAnEscapedPattern() {
        repo.search(fullFilters("salary"));
        String sql = capturedSql();
        assertThat(sql).doesNotContain("'%'||:q||'%'")
                .doesNotContain("'%'||:location||'%'")
                .doesNotContain("'%'||:company||'%'");
        assertThat(occurrences(sql, "ILIKE"))
                .as("every ILIKE needs ESCAPE '!': %s", sql)
                .isEqualTo(occurrences(sql, "ESCAPE '!'"));
        // :q stays raw for plainto_tsquery; only the LIKE side is a pattern
        assertThat(bound).contains("q", "qLike", "locationLike", "companyLike");
    }

    /**
     * {@code page}/{@code size} arrive straight from the query string, and this statement
     * splices them into {@code LIMIT :limit OFFSET :offset} itself. A negative offset is a
     * PostgreSQL error and an unbound parameter is a Hibernate one — both of which the HTTP
     * layer used to hand back to the browser as a 500.
     */
    /**
     * The company page's scope is an exact id, not the board's name facet. The two are different
     * questions — {@code ?company=Acme} on the board is *meant* to include Acme Labs, while a profile
     * page listing a sibling company's roles would be a wrong answer that shares its word with the
     * right one. The predicate and its bind are asserted together: a filter whose parameter is never
     * bound is a 500, not a wrong row.
     */
    @Test
    void aCompanyScopeFiltersByExactIdAndBindsIt() {
        UUID companyId = UUID.randomUUID();
        repo.search(new Filters(userId, null, null, null, null, null, companyId, null, null, "open",
                "match", 0, 100, null));

        String sql = capturedSql();
        assertThat(sql).contains("AND j.company_id = :companyId");
        assertThat(sql).doesNotContain("c.name ILIKE :companyLike");
        assertThat(params).containsEntry("companyId", companyId).containsEntry("status", "open");
        assertThat(placeholders(sql)).isEqualTo(bound);
    }

    @Test
    void aNegativePageBindsZeroOffsetNotANegativeOne() {
        repo.search(paged(-1, 12));
        assertThat(params).containsEntry("offset", 0L).containsEntry("limit", 12);
    }

    @Test
    void offsetIsThePageTimesTheClampedWindowSize() {
        repo.search(paged(3, 20));
        assertThat(params).containsEntry("offset", 60L);
        // size 1_000_000 is capped to 100 first, so the offset is 300 and not 3_000_000
        repo.search(paged(3, 1_000_000));
        assertThat(params).containsEntry("offset", 300L).containsEntry("limit", 100);
    }

    @Test
    void aZeroSizedWindowStillBindsTheLimitItsSqlReferences() {
        // ?size=0 used to mean "don't bind", on a statement that still says LIMIT :limit.
        repo.search(paged(0, 0));
        assertThat(placeholders(capturedSql())).isEqualTo(bound);
        assertThat(params).containsEntry("limit", 1).containsEntry("offset", 0L);
    }

    @Test
    void paginationIsBoundedInBothDirectionsBeforeItReachesTheDatabase() {
        Set<String> paging = Set.of("limit", "offset");
        int[] nasty = {Integer.MIN_VALUE, -1000, -1, 0, 1, 20, 100, 10_000, Integer.MAX_VALUE};
        for (int page : nasty) {
            for (int size : nasty) {
                bound.clear();
                params.clear();
                repo.search(paged(page, size));
                assertThat(bound).as("page=%d size=%d must both bind", page, size)
                        .containsAll(paging);
                assertThat((Long) params.get("offset")).isGreaterThanOrEqualTo(0L);
                assertThat((Integer) params.get("limit")).isBetween(1, 100);
            }
        }
    }

    private static int occurrences(String haystack, String needle) {
        int n = 0;
        for (int i = haystack.indexOf(needle); i >= 0; i = haystack.indexOf(needle, i + 1)) {
            n++;
        }
        return n;
    }

    // ------------------------------------------ hybrid ranking (relevance + query vector)

    @Test
    void hybridSearchRunsBothRankingPassesOverTheSameFilteredRows() {
        repo.search(hybrid("relevance"));
        String sql = capturedSql();
        assertThat(sql).contains("WITH filtered AS (")
                .contains(", keyword_rank AS (")
                .contains(", semantic_rank AS (")
                .contains(", scored AS (")
                .contains("WHERE tsv @@ plainto_tsquery('simple', :q)")
                .contains("vec <=> CAST(:vec AS vector)")
                .contains("ORDER BY rrf DESC");
        assertThat(placeholders(sql)).isEqualTo(bound);
        assertThat(bound).containsExactlyInAnyOrder("userId", "q", "qLike", "vec", "limit", "offset");
    }

    @Test
    void hybridCountsTheFusedSetItPagesOverAndNoWindow() {
        repo.count(hybrid("relevance"));
        String sql = capturedSql();
        assertThat(sql).contains("SELECT COUNT(*) FROM (SELECT id FROM scored) candidates");
        assertThat(sql).doesNotContain(":limit").doesNotContain(":offset");
        assertThat(placeholders(sql)).isEqualTo(bound);
        assertThat(bound).doesNotContain("limit", "offset");
    }

    @Test
    void anExplicitSortNeverRunsTheVectorPass() {
        // A caller who asks for an ordering is not asking for retrieval: sort=posted with a
        // vector in hand must stay on the plain statement, or its ORDER BY semantics would change.
        repo.search(hybrid("posted"));
        String sql = capturedSql();
        assertThat(sql).doesNotContain("<=>").doesNotContain("WITH filtered AS");
        assertThat(placeholders(sql)).isEqualTo(bound);
        assertThat(bound).doesNotContain("vec");
    }

    @Test
    void relevanceWithoutAVectorIsStillAKeywordRelevanceSearch() {
        repo.search(new Filters(userId, "java", null, null, null, null, null, null, null,
                "relevance", 0, 20, null));
        String sql = capturedSql();
        assertThat(sql).contains("ORDER BY ts_rank(j.tsv, plainto_tsquery('simple', :q)) DESC");
        assertThat(sql).doesNotContain("WITH filtered AS").doesNotContain(":vec");
        assertThat(placeholders(sql)).isEqualTo(bound);
    }

    @Test
    void relevanceOrderingWithoutAQueryRanksByRecencyAndBindsNoQ() {
        // :q appears in the relevance fragment only; blank q must not leave it unbound.
        repo.search(new Filters(userId, " ", null, null, null, null, null, null, null,
                "relevance", 0, 20, List.of(0.25)));
        String sql = capturedSql();
        assertThat(sql).contains("ORDER BY j.posted_at DESC");
        assertThat(sql).doesNotContain(":q");
        assertThat(placeholders(sql)).isEqualTo(bound);
        assertThat(bound).containsExactlyInAnyOrder("userId", "limit", "offset");
    }

    @Test
    void theQueryVectorIsBoundAsTextAndNeverSplicedIntoTheStatement() {
        repo.search(hybrid("relevance"));
        String sql = capturedSql();
        assertThat(sql).contains("CAST(:vec AS vector)");
        assertThat(sql).doesNotContain("0.25").doesNotContain("[-0.5");
        assertThat((String) params.get("vec")).isEqualTo("[0.25,-0.5]");
    }

    @Test
    void theSemanticPassIsCappedFlooredAndFusedWithTheToolConstants() {
        repo.search(hybrid("relevance"));
        String sql = capturedSql();
        assertThat(sql).contains("<= " + Double.toString(JobSearchRepository.SEMANTIC_DISTANCE_FLOOR))
                .contains("\n LIMIT " + JobSearchRepository.SEMANTIC_CANDIDATES)
                .contains("1.0 / (" + JobSearchRepository.RRF_K + " + k.rank)")
                .contains("1.0 / (" + JobSearchRepository.RRF_K + " + s.rank)");
    }

    @Test
    void theSemanticPassGuardsAgainstDimensionMismatchWithACaseExpression() {
        // A provider switch or a row written by a different model must not 500 the search;
        // the CASE guard makes the distance operator evaluate only on compatible rows,
        // so incompatible rows are simply skipped (the keyword pass still finds them).
        repo.search(hybrid("relevance"));
        String sql = capturedSql();
        assertThat(sql).contains("CASE")
                .contains("vector_dims(vec) = vector_dims(CAST(:vec AS vector))")
                .contains("THEN vec <=> CAST(:vec AS vector)")
                .contains("END <=");
    }

    /**
     * A paged list is a partition of its catalogue only if the ORDER BY is total, and every sort
     * key on this board can tie: two postings share a {@code posted_at}, a salary band repeats, a
     * title repeats, two matches score the same. Without a tie-break the row that falls between
     * two pages is whichever one the plan felt like, so the same URL answers different rows on two
     * visits. Each ordering ends in the id -- unique, and invisible to any reader who did not
     * already call the previous key equal.
     */
    @Test
    void everyOrderingEndsInTheRowsOwnIdSoPagesPartition() {
        List<String> sorts = List.of("posted", "salary", "title", "match", "relevance");
        for (String sort : sorts) {
            repo.search(fullFilters(sort));
        }
        ArgumentCaptor<String> statements = ArgumentCaptor.forClass(String.class);
        verify(em, times(sorts.size())).createNativeQuery(statements.capture());
        List<String> clauses = statements.getAllValues().stream().map(JobSearchRepositoryTest::orderByClause).toList();
        for (int i = 0; i < sorts.size(); i++) {
            assertThat(clauses.get(i))
                    .as("sort=%s must order by the row id last", sorts.get(i))
                    .endsWith("j.id ASC");
        }
    }

    @Test
    void theFusedRankingEndsInTheRowsOwnIdToo() {
        // The fused score is a sum of two reciprocal ranks, so a tie is the common case rather than
        // the edge one: two rows a single retriever ranked the same fuse identically.
        repo.search(hybrid("relevance"));
        assertThat(orderByClause(capturedSql())).isEqualTo("rrf DESC, posted_at DESC, id ASC");
    }

    /**
     * The rank <em>is</em> the score, so a tie inside a ranked window is not cosmetic: two rows the
     * keyword pass calls equal are numbered in whatever order the window visited them, which makes
     * the fused score of either row a different number on the next identical query -- and a total
     * outer ORDER BY then sorts by a number that is not the same number twice.
     */
    @Test
    void everyRankedWindowNumbersItsTiesByTheRowsOwnId() {
        repo.search(hybrid("relevance"));
        String sql = capturedSql();
        assertThat(sql).contains("ROW_NUMBER() OVER (ORDER BY ts_rank(tsv, plainto_tsquery('simple', :q)) DESC,\n"
                + "                               posted_at DESC, id) - 1 AS rank");
        assertThat(sql).contains("ROW_NUMBER() OVER (ORDER BY vec <=> CAST(:vec AS vector), posted_at DESC, id)"
                + " - 1 AS rank");
        // The semantic pass also cuts its own candidates at LIMIT, so a tie at that boundary would
        // drop a row the ranking never got to see.
        assertThat(sql).contains("END <= 0.98\n"
                + " ORDER BY vec <=> CAST(:vec AS vector), posted_at DESC, id\n"
                + " LIMIT " + JobSearchRepository.SEMANTIC_CANDIDATES);
    }

    @Test
    void hybridFacetsFilterTheSourceRowsWhileTheQueryPredicateStaysInItsPass() {
        Filters f = new Filters(userId, "java", List.of("spring"), "Remote", "remote", "Acme",
                100, 200, "open", "relevance", 0, 20, List.of(0.25, -0.5));
        repo.search(f);
        String sql = capturedSql();
        String source = sql.substring(0, sql.indexOf(", keyword_rank"));
        assertThat(source).doesNotContain(":q")
                .contains(":userId").contains(":locationLike").contains(":remote")
                .contains(":companyLike").contains(":minSalary").contains(":maxSalary")
                .contains(":status").contains(":skills");
        assertThat(placeholders(sql)).isEqualTo(bound);
    }

    /**
     * The clause list the panel contributed to a captured statement: everything from the first
     * {@code AND} after that board's own WHERE head up to the ordering that follows it. The head is
     * named rather than found by {@code lastIndexOf}, because the ranked board's last WHERE sits
     * inside a ranking CTE and slicing there would compare the wrong text. The FROM and the WHERE
     * head are the two boards' deliberate difference -- the shelf adds {@code saved_jobs} -- so what
     * is left has to be byte-identical, because it is one fragment running twice rather than a
     * paraphrase of it. Comparing the two statements the repository built is the point: a helper
     * called twice on its own would say the same thing about itself no matter what either board did.
     */
    private static String filterClauses(String sql) {
        int where = sql.indexOf("WHERE 1=1");
        if (where < 0) {
            where = sql.indexOf("WHERE sj.user_id = :userId");
        }
        assertThat(where).isGreaterThan(0);
        int and = sql.indexOf(" AND ", where);
        assertThat(and).isGreaterThan(where);
        int order = sql.indexOf(" ORDER BY ", where);
        int limit = sql.indexOf(" LIMIT ", where);
        int end = sql.length();
        if (order >= 0 || limit >= 0) {
            end = order < 0 ? limit : (limit < 0 ? order : Math.min(order, limit));
        }
        return sql.substring(and, end).trim();
    }

    /** The panel's whole predicate set, spelled the same way for both boards. */
    private static final String SHELF_Q = "java";
    private static final List<String> SHELF_SKILLS = List.of("spring", "kafka");
    private static final String SHELF_LOCATION = "Remote";
    private static final String SHELF_REMOTE = "remote";
    private static final String SHELF_COMPANY = "Acme";

    private SavedBoard shelf() {
        // 74.2: page 2 of size 7 asks the server for rows 14..20, and the count is the server's own
        // COUNT(*) over the same fragment.
        return new SavedBoard(userId, SHELF_Q, SHELF_SKILLS, SHELF_LOCATION, SHELF_REMOTE,
                SHELF_COMPANY, 100, 200, 2, 7);
    }

    private Filters boardWithoutStatus() {
        return new Filters(userId, SHELF_Q, SHELF_SKILLS, SHELF_LOCATION, SHELF_REMOTE,
                SHELF_COMPANY, 100, 200, "", "posted", 0, 20, null);
    }

    @Test
    void theSavedBoardBindsExactlyTheParametersItsSqlReferences() {
        repo.saved(shelf());
        String sql = capturedSql();
        assertThat(placeholders(sql)).isEqualTo(bound);
        assertThat(bound).containsExactlyInAnyOrder("userId", "q", "qLike", "locationLike", "remote",
                "companyLike", "minSalary", "maxSalary", "skills", "limit", "offset");
        assertThat(sql).contains("FROM saved_jobs sj").contains("JOIN jobs j ON j.id = sj.job_id")
                .contains("WHERE sj.user_id = :userId");
    }

    /**
     * The headline 74.1 exists for. The discover board and the shelf are two statements -- one
     * answers the catalogue, one answers what the reader kept -- and every predicate after their
     * differing FROM heads has to be the same text. A paraphrase would let a word mean
     * "title or company" on one tab and "title, company or description" on the other, which is the
     * divergence {@code lib/job-filter.ts} used to document as "narrower than Discover, never
     * wider".
     */
    @Test
    void theSavedBoardAppendsTheDiscoverBoardsOwnPredicateFragment() {
        repo.search(boardWithoutStatus());
        repo.saved(shelf());
        ArgumentCaptor<String> statements = ArgumentCaptor.forClass(String.class);
        verify(em, times(2)).createNativeQuery(statements.capture());
        String discover = filterClauses(statements.getAllValues().get(0));
        String shelf = filterClauses(statements.getAllValues().get(1));
        assertThat(shelf).isEqualTo(discover);
        // The description half, which the client's copy could never reach.
        assertThat(discover).contains("j.tsv @@ plainto_tsquery('simple', :q)");
    }

    @Test
    void theSavedBoardEndsItsOrderInTheBookmarkKeySoTheShelfIsATotalOrder() {
        // `created_at` is a column default, so bookmarks written by one action share it to the
        // microsecond; the old derived read ordered by that column alone.
        repo.saved(shelf());
        assertThat(orderByClause(capturedSql())).isEqualTo("sj.created_at DESC, sj.job_id ASC");
    }

    @Test
    void theSavedCountAndThePageReadCarryTheSameFragment() {
        // 74.2: the pager's number and the rows on the page are two reads of one WHERE. If they
        // ever diverge the pager promises rows the shelf would not draw.
        repo.savedCount(shelf());
        repo.saved(shelf());
        ArgumentCaptor<String> statements = ArgumentCaptor.forClass(String.class);
        verify(em, times(2)).createNativeQuery(statements.capture());
        String countSql = statements.getAllValues().get(0);
        String pageSql = statements.getAllValues().get(1);

        assertThat(countSql).contains("SELECT COUNT(*)").contains("WHERE sj.user_id = :userId")
                .doesNotContain(" LIMIT ").doesNotContain(" OFFSET ").doesNotContain(" ORDER BY ");
        assertThat(pageSql).contains("LIMIT :limit OFFSET :offset")
                .contains(" ORDER BY sj.created_at DESC, sj.job_id ASC");
        // The predicate region both statements share, byte for byte.
        int countWhere = countSql.indexOf("WHERE sj.user_id = :userId");
        int pageWhere = pageSql.indexOf("WHERE sj.user_id = :userId");
        int pageOrder = pageSql.indexOf(" ORDER BY ", pageWhere);
        assertThat(countSql.substring(countWhere).trim())
                .isEqualTo(pageSql.substring(pageWhere, pageOrder).trim());
    }

    @Test
    void theSavedCountWalksTheFragmentWithoutAWindow() {
        // The pager's total is the count over the same predicates; it answers the whole matching
        // shelf whatever window the URL asked for, and it never binds a limit of its own.
        repo.savedCount(new SavedBoard(userId, SHELF_Q, null, null, null, null, null, null, 0, 0));
        String sql = capturedSql();
        assertThat(sql).doesNotContain("LIMIT").doesNotContain("OFFSET")
                .contains("WHERE sj.user_id = :userId");
        assertThat(bound).doesNotContain("limit", "offset");
        // And it names the reader's own rows and no one else's, even with no predicates at all.
        assertThat(sql).contains("sj.user_id = :userId");
    }
}
