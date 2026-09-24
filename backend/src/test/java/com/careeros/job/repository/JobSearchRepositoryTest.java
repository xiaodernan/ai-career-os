package com.careeros.job.repository;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.job.repository.JobSearchRepository.Filters;
import jakarta.persistence.EntityManager;
import jakarta.persistence.Query;
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
 *     before it is spliced into {@code LIMIT}/{@code OFFSET}.
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

    private Filters fullFilters(String sort) {
        return new Filters(userId, "java", List.of("spring", "kafka"), "Remote", "remote",
                "Acme", 100, 200, "open", sort, 2, 25);
    }

    /** Sparse filters, so the only bound parameters besides userId are the paging ones. */
    private Filters paged(int page, int size) {
        return new Filters(userId, null, null, null, null, null, null, null, null, null, page, size);
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

    @Test
    void sparseFiltersBindNoUnusedParameters() {
        Filters f = new Filters(userId, null, null, null, null, null, null, null, null,
                null, 0, 10);
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
}
