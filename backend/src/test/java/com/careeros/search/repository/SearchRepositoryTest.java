package com.careeros.search.repository;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import jakarta.persistence.EntityManager;
import jakarta.persistence.Query;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/**
 * Guardrails for the cross-entity global-search native SQL (plain Mockito — no DB):
 * (1) each group's statement binds EXACTLY the named parameters it references (so a future
 *     filter/param added on one side but not the other is caught here, not in production as a
 *     "parameter not bound" 500); (2) the user query term is bound as a parameter, never
 *     interpolated into SQL; (3) the user-scoped vs shared-catalog (companies/jobs) split is
 *     preserved. The only other coverage of these queries is the Docker-only integration test.
 */
class SearchRepositoryTest {

    private final UUID userId = UUID.randomUUID();
    private EntityManager em;
    private Query query;
    private SearchRepository repo;
    private String lastSql;
    private Set<String> bound;

    @BeforeEach
    void setUp() {
        em = mock(EntityManager.class);
        query = mock(Query.class);
        repo = new SearchRepository(em);
        lastSql = "";
        bound = new HashSet<>();
        when(em.createNativeQuery(anyString())).thenAnswer(inv -> {
            lastSql = inv.getArgument(0);
            return query;
        });
        doAnswer(inv -> {
            bound.add(inv.getArgument(0));
            return query;
        }).when(query).setParameter(anyString(), any());
        when(query.getResultList()).thenReturn(List.of());
    }

    private static Set<String> placeholders(String sql) {
        Set<String> names = new HashSet<>();
        Matcher m = Pattern.compile(":(\\w+)").matcher(sql);
        while (m.find()) {
            names.add(m.group(1));
        }
        return names;
    }

    @Test
    void everyGroupBindsExactlyTheParametersItsSqlReferences() {
        repo.jobs(userId, "java", 5, null);
        assertThat(placeholders(lastSql)).isEqualTo(bound);

        bound.clear();
        repo.resumes(userId, "java", 5);
        assertThat(placeholders(lastSql)).isEqualTo(bound);

        bound.clear();
        repo.notes(userId, "java", 5);
        assertThat(placeholders(lastSql)).isEqualTo(bound);

        bound.clear();
        repo.conversations(userId, "java", 5);
        assertThat(placeholders(lastSql)).isEqualTo(bound);

        bound.clear();
        repo.applications(userId, "java", 5);
        assertThat(placeholders(lastSql)).isEqualTo(bound);
    }

    @Test
    void companiesIsSharedCatalogBoundByQueryAndLimitOnly() {
        repo.companies("Acme", 5);
        assertThat(lastSql).doesNotContain(":userId");
        // companies has no tsvector, so the term arrives only as the escaped LIKE pattern
        assertThat(bound).containsExactlyInAnyOrder("qLike", "limit");
    }

    @Test
    void jobsQueryTermIsBoundNotInterpolated() {
        String evil = "x'; DROP TABLE users; --";
        repo.jobs(userId, evil, 5, null);
        // the term must reach the DB only as a bound :q parameter
        assertThat(lastSql).contains(":q").doesNotContain("DROP TABLE").doesNotContain(evil);
        assertThat(bound).contains("q");
    }

    @Test
    void userOwnedGroupsBindUserIdButCompaniesDoesNot() {
        assertThat(boundOf(r -> r.resumes(userId, "q", 1))).contains("userId");
        assertThat(boundOf(r -> r.notes(userId, "q", 1))).contains("userId");
        assertThat(boundOf(r -> r.applications(userId, "q", 1))).contains("userId");
        assertThat(boundOf(r -> r.conversations(userId, "q", 1))).contains("userId");
        assertThat(boundOf(r -> r.companies("q", 1))).doesNotContain("userId");
        // jobs are catalog rows: :userId is not in the statement even though the caller has one
        assertThat(boundOf(r -> r.jobs(userId, "q", 1, null))).doesNotContain("userId");
    }

    @Test
    void theHybridJobsStatementProjectsWhatItSortsByAndBindsOnlyWhatItReferences() {
        // Regression: the fused CTE projected every column the mapper reads but not posted_at,
        // while the outer ORDER BY sorted by it. Text assertions cannot see that, so the statement
        // compiled, passed review and then failed on the first real database with
        // "column posted_at does not exist" -- i.e. every global search answered 500.
        repo.jobs(userId, "java", 5, List.of(0.25, -0.5));
        assertThat(lastSql).contains("WITH filtered AS (").contains("CAST(:vec AS vector)");
        // The board's semantic pass guards the distance operator with this CASE; the palette's had
        // the same operator on rows another provider may have written and no guard at all.
        assertThat(lastSql)
                .contains("vector_dims(vec) = vector_dims(CAST(:vec AS vector))");
        assertThat(lastSql).doesNotContain("0.25").doesNotContain("[-0.5");
        assertThat(placeholders(lastSql)).isEqualTo(bound);
        assertThat(bound).containsExactlyInAnyOrder("q", "qLike", "limit", "vec");
        String scored = lastSql.substring(lastSql.indexOf("scored AS ("), lastSql.indexOf("SELECT id, title"));
        assertThat(scored)
                .as("the outer ORDER BY sorts by posted_at, so the CTE must project it")
                .contains("f.posted_at");
    }

    /**
     * The palette is a top-N list, not a paged one, but the boundary is still a decision: a tie on
     * the last sort key lets PostgreSQL choose which of the tied rows the LIMIT keeps, so the same
     * query can answer a different set on two visits. Every channel therefore ends its ORDER BY in
     * the row's own id, except companies, whose name the schema declares unique -- there the order
     * is already total and a second key would be noise.
     */
    @Test
    void everyChannelsOrderingEndsInTheRowsOwnId() {
        repo.jobs(userId, "java", 5, null);
        assertThat(orderByClause(lastSql)).isEqualTo(
                "ts_rank(j.tsv, plainto_tsquery('simple', :q)) DESC, j.posted_at DESC, j.id ASC");

        repo.jobs(userId, "java", 5, List.of(0.25, -0.5));
        assertThat(orderByClause(lastSql)).isEqualTo("rrf DESC, posted_at DESC, id ASC");
        // The rank windows number the ties, so they need the same tie-break: a rank is a score.
        assertThat(lastSql).contains("posted_at DESC, id) - 1 AS rank");
        // Collapsed, because a text block strips its incidental indentation: the statement the
        // database sees has five leading spaces where the source has twenty-one.
        assertThat(lastSql.replaceAll("\\s+", " "))
                .contains("ORDER BY vec <=> CAST(:vec AS vector), posted_at DESC, id LIMIT 50");

        repo.companies("Acme", 5);
        assertThat(orderByClause(lastSql)).isEqualTo("name ASC");

        repo.resumes(userId, "java", 5);
        assertThat(orderByClause(lastSql)).isEqualTo("updated_at DESC, id ASC");
        repo.notes(userId, "java", 5);
        assertThat(orderByClause(lastSql)).isEqualTo("updated_at DESC, id ASC");
        repo.conversations(userId, "java", 5);
        assertThat(orderByClause(lastSql)).isEqualTo("cv.updated_at DESC, cv.id ASC");
        repo.applications(userId, "java", 5);
        assertThat(orderByClause(lastSql)).isEqualTo("updated_at DESC, id ASC");
    }

    /** The outer ORDER BY of a captured statement, whitespace-collapsed, without its LIMIT. */
    private static String orderByClause(String sql) {
        int at = sql.lastIndexOf("ORDER BY ");
        assertThat(at).isGreaterThanOrEqualTo(0);
        String rest = sql.substring(at + "ORDER BY ".length());
        int limit = rest.indexOf(" LIMIT");
        return (limit < 0 ? rest : rest.substring(0, limit)).trim().replaceAll("\\s+", " ");
    }

    @Test
    void withoutAVectorTheJobsStatementStaysKeywordOnlyAndBindsNoVector() {
        repo.jobs(userId, "java", 5, List.of());
        assertThat(lastSql).doesNotContain("CAST(:vec AS vector)").doesNotContain("scored AS (");
        assertThat(placeholders(lastSql)).isEqualTo(bound);
        assertThat(bound).doesNotContain("vec");
    }


    private Set<String> boundOf(java.util.function.Consumer<SearchRepository> call) {
        lastSql = "";
        bound.clear();
        call.accept(repo);
        return new HashSet<>(bound);
    }

    @Test
    void everyLikeMatchTreatsTheTermAsALiteralNotAPattern() {
        // '%'||:q||'%' hands user text to LIKE verbatim: "a_b" then matches "axb", "%"
        // matches every row, and a term with a backslash finds nothing at all.
        List<java.util.function.Consumer<SearchRepository>> calls = new java.util.ArrayList<>();
        calls.add(r -> r.jobs(userId, "a_b", 1, null));
        calls.add(r -> r.companies("a_b", 1));
        calls.add(r -> r.resumes(userId, "a_b", 1));
        calls.add(r -> r.notes(userId, "a_b", 1));
        calls.add(r -> r.conversations(userId, "a_b", 1));
        calls.add(r -> r.applications(userId, "a_b", 1));
        for (java.util.function.Consumer<SearchRepository> call : calls) {
            boundOf(call);
            assertThat(lastSql).as("raw term used as a LIKE pattern").doesNotContain("'%'||:q||'%'");
            assertThat(occurrences(lastSql, "ILIKE"))
                    .as("every ILIKE needs ESCAPE '!': %s", lastSql)
                    .isEqualTo(occurrences(lastSql, "ESCAPE '!'"));
            assertThat(bound).as("escaped pattern bound for %s", lastSql).contains("qLike");
        }
        // ':q' survives only where a tsquery still consumes it, and the escaped value is a
        // separate bind — one parameter cannot serve both roles.
        boundOf(r -> r.jobs(userId, "a_b", 1, null));
        assertThat(bound).contains("q", "qLike");
        boundOf(r -> r.notes(userId, "a_b", 1));
        assertThat(bound).doesNotContain("q");
    }

    private static int occurrences(String haystack, String needle) {
        int n = 0;
        for (int i = haystack.indexOf(needle); i >= 0; i = haystack.indexOf(needle, i + 1)) {
            n++;
        }
        return n;
    }
}
