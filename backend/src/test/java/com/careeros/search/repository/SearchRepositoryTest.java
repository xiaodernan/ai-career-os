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
        repo.jobs(userId, "java", 5);
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
        assertThat(bound).containsExactlyInAnyOrder("q", "limit");
    }

    @Test
    void jobsQueryTermIsBoundNotInterpolated() {
        String evil = "x'; DROP TABLE users; --";
        repo.jobs(userId, evil, 5);
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
        assertThat(boundOf(r -> r.jobs(userId, "q", 1))).doesNotContain("userId");
    }

    private Set<String> boundOf(java.util.function.Consumer<SearchRepository> call) {
        lastSql = "";
        bound.clear();
        call.accept(repo);
        return new HashSet<>(bound);
    }
}
