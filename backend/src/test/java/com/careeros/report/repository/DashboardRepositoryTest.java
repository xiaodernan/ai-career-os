package com.careeros.report.repository;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.report.dto.DashboardDtos.RecommendedJob;
import jakarta.persistence.EntityManager;
import jakarta.persistence.Query;
import java.math.BigDecimal;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

/**
 * Recommended-jobs read: the query attaches the viewer's latest match via a LATERAL join, so
 * the row -> {@link RecommendedJob} cast mapping and the 0..1 match float handling are the
 * drift-prone parts (the frontend renders this as the match ring). Plain Mockito, no DB.
 */
class DashboardRepositoryTest {

    private final UUID userId = UUID.randomUUID();
    private final UUID jobId = UUID.randomUUID();
    private final UUID matchId = UUID.randomUUID();
    private EntityManager em;
    private Query query;
    private DashboardRepository repo;
    private Set<String> bound;
    private String lastSql;

    @BeforeEach
    void setUp() {
        em = mock(EntityManager.class);
        query = mock(Query.class);
        repo = new DashboardRepository(em);
        bound = new HashSet<>();
        lastSql = "";
        when(em.createNativeQuery(anyString())).thenAnswer(inv -> {
            lastSql = inv.getArgument(0);
            return query;
        });
        doAnswer(inv -> {
            bound.add(inv.getArgument(0));
            return query;
        }).when(query).setParameter(anyString(), any());
    }

    private void rows(List<Object[]> result) {
        when(query.getResultList()).thenReturn(result);
    }

    @Test
    void bindsExactlyTheReferencedParameters() {
        rows(List.of());
        repo.recommendedJobs(userId, 8);
        Set<String> names = new HashSet<>();
        Matcher m = Pattern.compile(":(\\w+)").matcher(lastSql);
        while (m.find()) {
            names.add(m.group(1));
        }
        assertThat(names).isEqualTo(bound);
        assertThat(bound).containsExactlyInAnyOrder("userId", "limit");
    }

    @Test
    void mapsFullRowToRecommendedJobInColumnOrder() {
        Object[] row = new Object[]{jobId, "Backend Eng", "Acme", "Remote", "remote",
                Timestamp.from(Instant.parse("2026-01-02T03:04:05Z")), 0.75, matchId};
        List<Object[]> data = new ArrayList<>();
        data.add(row);
        rows(data);

        RecommendedJob job = repo.recommendedJobs(userId, 8).get(0);
        assertThat(job.id()).isEqualTo(jobId);
        assertThat(job.title()).isEqualTo("Backend Eng");
        assertThat(job.companyName()).isEqualTo("Acme");
        assertThat(job.location()).isEqualTo("Remote");
        assertThat(job.remoteType()).isEqualTo("remote");
        assertThat(job.postedAt().toInstant()).isEqualTo(Instant.parse("2026-01-02T03:04:05Z"));
        assertThat(job.matchOverall()).isEqualTo(0.75f);
        assertThat(job.matchId()).isEqualTo(matchId);
    }

    @Test
    void nullMatchBecomesNullScoreAndIdWithoutNpe() {
        Object[] row = new Object[]{jobId, "T", "C", "L", "onsite",
                Timestamp.from(Instant.now()), null, null};
        List<Object[]> data = new ArrayList<>();
        data.add(row);
        rows(data);

        RecommendedJob job = repo.recommendedJobs(userId, 8).get(0);
        assertThat(job.matchOverall()).isNull();
        assertThat(job.matchId()).isNull();
    }

    @Test
    void matchScoreAcceptsAnyNumericColumnRepresentation() {
        // pg may surface the float as Double, Float or BigDecimal — the cast is via Number
        Object[] row = new Object[]{jobId, "T", "C", "L", "onsite",
                Timestamp.from(Instant.now()), new BigDecimal("0.62"), matchId};
        List<Object[]> data = new ArrayList<>();
        data.add(row);
        rows(data);
        assertThat(repo.recommendedJobs(userId, 8).get(0).matchOverall()).isEqualTo(0.62f);
    }

    @Test
    void queryIsScopedToViewerAndExcludesAppliedOpenJobs() {
        rows(List.of());
        repo.recommendedJobs(userId, 8);
        assertThat(lastSql).contains("jm.user_id = :userId")
                .contains("a.user_id = :userId")
                .contains("j.status = 'open'")
                .contains("NOT EXISTS");
        verify(query).setParameter("limit", 8);
    }
}
