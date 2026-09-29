package com.careeros.report.repository;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.report.dto.DashboardDtos.AttentionItem;
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
 * Dashboard reads: the recommended-jobs query attaches the viewer's latest match via a LATERAL
 * join, so the row -> {@link RecommendedJob} cast mapping and the 0..1 match float handling are
 * the drift-prone parts (the frontend renders this as the match ring); the two stat aggregates
 * are single-value queries whose null/zero distinction the stat strip depends on. Plain Mockito,
 * no DB.
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

    private void single(Object result) {
        when(query.getSingleResult()).thenReturn(result);
    }

    /**
     * Every {@code :name} the last statement references must be bound, and nothing may be bound
     * that the statement does not reference — a drifted parameter name fails at runtime with a
     * Hibernate IllegalArgumentException rather than returning wrong rows.
     */
    private void assertBindsExactly(String... names) {
        Set<String> referenced = new HashSet<>();
        Matcher m = Pattern.compile(":(\\w+)").matcher(lastSql);
        while (m.find()) {
            referenced.add(m.group(1));
        }
        assertThat(referenced).containsExactlyInAnyOrder(names);
        assertThat(bound).isEqualTo(referenced);
    }

    @Test
    void bindsExactlyTheReferencedParameters() {
        rows(List.of());
        repo.recommendedJobs(userId, 8);
        assertBindsExactly("userId", "limit");
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

    @Test
    void averageMatchCollapsesToTheNewestMatchPerJob() {
        single(0.66d);
        Float avg = repo.averageMatch(userId);
        assertThat(avg).isEqualTo(0.66f);
        // One job re-scored five times must weigh as much as one scored once.
        assertThat(lastSql).contains("SELECT DISTINCT ON (jm.job_id)")
                .contains("ORDER BY jm.job_id, jm.created_at DESC, jm.id DESC")
                .contains("jm.user_id = :userId");
        assertBindsExactly("userId");
        assertThat(lastSql).doesNotContain(userId.toString());
    }

    @Test
    void unscoredUserHasNoAverageRatherThanZero() {
        // avg() over an empty set comes back NULL, not 0.0 — the card hides on null, a 0% ring
        // would claim the user scored badly instead of never having scored.
        single(null);
        assertThat(repo.averageMatch(userId)).isNull();
    }

    @Test
    void averageMatchAcceptsWhateverNumericTypeTheDriverReturns() {
        single(new BigDecimal("0.713"));
        assertThat(repo.averageMatch(userId)).isEqualTo(0.713f);
    }

    @Test
    void needsAttentionCountsOnlyUnresolvedApplications() {
        single(3L);
        assertThat(repo.needsAttention(userId, 14)).isEqualTo(3L);
        assertThat(lastSql).contains("a.user_id = :userId")
                .contains("a.status NOT IN ('offer', 'rejected')")
                .contains("a.updated_at < now() - make_interval(days => :staleDays)")
                .contains("a.reminder_at IS NOT NULL AND a.reminder_at <= now()");
        verify(query).setParameter("staleDays", 14);
        assertBindsExactly("userId", "staleDays");
    }

    @Test
    void needsAttentionOfNothingIsZeroRatherThanMissing() {
        // count(*) always returns a row, so the primitive long path holds: the stat card shows 0.
        single(0L);
        assertThat(repo.needsAttention(userId, 14)).isZero();
    }

    @Test
    void attentionMapsTheRowAndItsReasonInColumnOrder() {
        UUID applicationId = UUID.randomUUID();
        Object[] row = new Object[]{applicationId, "Senior Backend Engineer", "Acme", "applied",
                "reminder_due", Timestamp.from(Instant.parse("2026-09-01T09:00:00Z")),
                Timestamp.from(Instant.parse("2026-08-01T09:00:00Z"))};
        List<Object[]> data = new ArrayList<>();
        data.add(row);
        rows(data);

        AttentionItem item = repo.attention(userId, 14, 5).get(0);
        assertThat(item.id()).isEqualTo(applicationId);
        assertThat(item.title()).isEqualTo("Senior Backend Engineer");
        assertThat(item.companyName()).isEqualTo("Acme");
        assertThat(item.status()).isEqualTo("applied");
        assertThat(item.reason()).isEqualTo("reminder_due");
        assertThat(item.reminderAt().toInstant()).isEqualTo(Instant.parse("2026-09-01T09:00:00Z"));
        assertThat(item.updatedAt().toInstant()).isEqualTo(Instant.parse("2026-08-01T09:00:00Z"));
    }

    @Test
    void attentionToleratesARowWithNoCompanyAndNoReminder() {
        // An application added by hand has neither: no `company_id` to join, and no reminder until
        // the user sets one. The card renders the typed-in name (COALESCE), and a `stale` row has
        // no instant to show -- both have to survive the mapping.
        Object[] row = new Object[]{UUID.randomUUID(), "Take-home", "Somewhere", "oa",
                "stale", null, Timestamp.from(Instant.now())};
        List<Object[]> data = new ArrayList<>();
        data.add(row);
        rows(data);

        AttentionItem item = repo.attention(userId, 14, 5).get(0);
        assertThat(item.reason()).isEqualTo("stale");
        assertThat(item.reminderAt()).isNull();
    }

    @Test
    void attentionAsksForTheDueRemindersFirstThenTheLongestIdle() {
        rows(List.of());
        repo.attention(userId, 14, 5);
        assertThat(lastSql)
                .contains("LEFT JOIN companies c ON c.id = a.company_id")
                .contains("COALESCE(c.name, a.company_name)")
                .contains("ORDER BY (a.reminder_at IS NOT NULL AND a.reminder_at <= now()) DESC")
                .contains("a.updated_at ASC")
                .contains("LIMIT :limit");
        assertBindsExactly("userId", "staleDays", "limit");
    }

    @Test
    void theListIsFilteredByExactlyTheClauseTheCountIs() {
        rows(List.of());
        repo.attention(userId, 14, 5);
        String listSql = squeeze(lastSql);
        single(0L);
        repo.needsAttention(userId, 14);
        String countSql = squeeze(lastSql);

        // Not "both mention the rule" but "the count's whole predicate is inside the list's": the
        // strip and the card are one question asked twice, and a second copy of the clause is how
        // they stop agreeing.
        String predicate = countSql.substring(countSql.indexOf("a.status NOT IN"));
        assertThat(predicate).contains("a.reminder_at <= now()");
        assertThat(listSql).contains(predicate);
    }

    @Test
    void theListStatementKeepsTheSpaceThatJoinsTheSharedPredicate() {
        // The predicate is concatenated onto a text block, and a text block strips trailing
        // whitespace from every line: without this, `AND ` arrives as `AND` and Postgres rejects
        // the statement with `syntax error at or near "ANDa"`. It is a runtime-only failure —
        // the count query below spells the same join in an ordinary string, so the strip's
        // number kept working while the card's rows 500'd the whole dashboard.
        rows(List.of());
        repo.attention(userId, 14, 5);

        assertThat(squeeze(lastSql))
                .contains("WHERE a.user_id = :userId AND a.status NOT IN ('offer', 'rejected')");
        assertThat(lastSql).doesNotContain("ANDa");
    }

    /** Statement text with every run of whitespace collapsed, so the comparison is about SQL. */
    private static String squeeze(String sql) {
        return sql.replaceAll("\\s+", " ").trim();
    }
}
