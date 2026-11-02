package com.careeros.auth.retention;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.auth.repository.EmailChangeTokenRepository;
import com.careeros.auth.repository.PasswordResetTokenRepository;
import com.careeros.auth.repository.RefreshTokenRepository;
import com.careeros.config.AppProperties;
import com.careeros.knowledge.service.RetiredEvidencePurger;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.time.Instant;
import java.time.OffsetDateTime;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/**
 * Roadmap 28.1's two promises, neither of which an integration test can pin without a clock:
 *
 * <p>One — the cutoff is the sweep's clock minus the grace window, not "expired now". A row
 * whose expiry is recent enough to still matter to a late request or a support investigation
 * must survive even though it is technically expired; only rows past the window go.
 *
 * <p>Two — one table's failure is one table's failure. The three deletes run in separate
 * transactions so a lock timeout on refresh tokens leaves reset and address-change rows pruned;
 * the failed table is named in the summary and, deliberately, exports no counter, so a stale
 * reading can never be mistaken for a fresh one.
 *
 * <p>And 28.2's one: the heartbeat answers whether the schedule ran, which no deletion count
 * can. It starts at boot rather than at zero, and a pass that failed every table still moves
 * it — the failures are the counters' story, not the clock's.
 *
 * <p>44.3 adds the evidence phase and the same two promises to it: the window on a retired
 * document is its own knob, so moving the credential grace cannot quietly start purging audit
 * records early; the chunks the cascade took get their own reading, because counting only the
 * rows would understate the night; and a purge that skipped a row a source still names is an
 * anomaly in the log, not a failed table with no counter.
 */
class RetentionSweeperTest {

    private static final OffsetDateTime NOW = OffsetDateTime.parse("2026-10-29T04:47:00Z");

    private final RefreshTokenRepository refreshTokens = mock(RefreshTokenRepository.class);
    private final PasswordResetTokenRepository resetTokens = mock(PasswordResetTokenRepository.class);
    private final EmailChangeTokenRepository emailChangeTokens =
            mock(EmailChangeTokenRepository.class);
    private final RetiredEvidencePurger evidence = mock(RetiredEvidencePurger.class);
    private final SimpleMeterRegistry registry = new SimpleMeterRegistry();
    private final AppProperties props = new AppProperties();
    private final RetentionSweeper sweeper = new RetentionSweeper(
            refreshTokens, resetTokens, emailChangeTokens, evidence, props,
            new RetentionMetrics(registry));

    /**
     * Held in a field so it cannot be collected before the read: Micrometer's gauge keeps its
     * object weakly, and a discarded metrics instance answers {@code NaN} once the collector
     * takes it -- which it does under a full suite, not when this class runs alone.
     */
    private RetentionMetrics freshMetrics;

    @BeforeEach
    void defaultCounts() {
        when(refreshTokens.deleteExpiredBefore(NOW.minusDays(30))).thenReturn(3);
        when(resetTokens.deleteExpiredBefore(NOW.minusDays(30))).thenReturn(5);
        when(emailChangeTokens.deleteExpiredBefore(NOW.minusDays(30))).thenReturn(0);
        // Any cutoff: the tests that care which window the phase used verify the argument, and a
        // stub pinned to one date would make every other pass look like a failed purge.
        when(evidence.purgeBefore(any()))
                .thenReturn(new RetiredEvidencePurger.Purge(2, 40, 0));
    }

    @Test
    void theCutoffIsTheClockMinusTheGraceWindowNotExpiryItself() {
        RetentionSweeper.Sweep sweep = sweeper.sweep(NOW);

        verify(refreshTokens).deleteExpiredBefore(NOW.minusDays(30));
        verify(resetTokens).deleteExpiredBefore(NOW.minusDays(30));
        verify(emailChangeTokens).deleteExpiredBefore(NOW.minusDays(30));
        assertThat(sweep.deleted()).containsEntry(RetentionSweeper.REFRESH_TOKENS, 3L)
                .containsEntry(RetentionSweeper.PASSWORD_RESET_TOKENS, 5L)
                .containsEntry(RetentionSweeper.EMAIL_CHANGE_TOKENS, 0L);
        assertThat(sweep.failed()).isEmpty();
    }

    @Test
    void everySweptTableLeavesACounterTaggedWithItsName() {
        sweeper.sweep(NOW);

        assertThat(count(RetentionSweeper.REFRESH_TOKENS)).isEqualTo(3.0);
        assertThat(count(RetentionSweeper.PASSWORD_RESET_TOKENS)).isEqualTo(5.0);
        assertThat(count(RetentionSweeper.EMAIL_CHANGE_TOKENS)).isZero();
        assertThat(heartbeat()).isEqualTo(NOW.toEpochSecond());
    }

    @Test
    void theHeartbeatMovesEvenWhenEveryTableFailed() {
        when(refreshTokens.deleteExpiredBefore(NOW.minusDays(30)))
                .thenThrow(new IllegalStateException("database is down"));
        when(resetTokens.deleteExpiredBefore(NOW.minusDays(30)))
                .thenThrow(new IllegalStateException("database is down"));
        when(emailChangeTokens.deleteExpiredBefore(NOW.minusDays(30)))
                .thenThrow(new IllegalStateException("database is down"));

        RetentionSweeper.Sweep sweep = sweeper.sweep(NOW);

        assertThat(sweep.failed()).containsExactly(
                RetentionSweeper.REFRESH_TOKENS,
                RetentionSweeper.PASSWORD_RESET_TOKENS,
                RetentionSweeper.EMAIL_CHANGE_TOKENS);
        assertThat(heartbeat()).isEqualTo(NOW.toEpochSecond());
    }

    @Test
    void theHeartbeatStartsAtBootNotAtZeroSoAFreshDeployIsNotStale() {
        SimpleMeterRegistry freshRegistry = new SimpleMeterRegistry();
        long before = Instant.now().getEpochSecond();
        freshMetrics = new RetentionMetrics(freshRegistry);
        long after = Instant.now().getEpochSecond();

        Gauge gauge = freshRegistry.find(RetentionMetrics.LAST_SWEEP).gauge();
        assertThat(gauge).as("the heartbeat is registered when the bean is built").isNotNull();
        assertThat(gauge.value()).isBetween((double) before, (double) after);
    }

    private double heartbeat() {
        Gauge gauge = registry.find(RetentionMetrics.LAST_SWEEP).gauge();
        assertThat(gauge).as("the heartbeat gauge is registered at boot").isNotNull();
        return gauge.value();
    }

    @Test
    void aFailingTableDoesNotStopTheOthersAndLeavesNoCounter() {
        when(refreshTokens.deleteExpiredBefore(NOW.minusDays(30)))
                .thenThrow(new IllegalStateException("lock timeout"));

        RetentionSweeper.Sweep sweep = sweeper.sweep(NOW);

        assertThat(sweep.failed()).containsExactly(RetentionSweeper.REFRESH_TOKENS);
        assertThat(sweep.deleted()).containsEntry(RetentionSweeper.PASSWORD_RESET_TOKENS, 5L)
                .containsEntry(RetentionSweeper.EMAIL_CHANGE_TOKENS, 0L)
                .doesNotContainKey(RetentionSweeper.REFRESH_TOKENS);
        verify(resetTokens).deleteExpiredBefore(NOW.minusDays(30));
        verify(emailChangeTokens).deleteExpiredBefore(NOW.minusDays(30));
        assertThat(counter(RetentionSweeper.REFRESH_TOKENS)).isNull();
        assertThat(count(RetentionSweeper.PASSWORD_RESET_TOKENS)).isEqualTo(5.0);
    }

    @Test
    void aNegativeGraceWindowIsClampedToZeroRatherThanDeletingFutureRows() {
        props.getRetention().setExpiredTokenDays(-5);
        props.getRetention().setRetiredDocumentDays(-5);

        RetentionSweeper.Sweep sweep = sweeper.sweep(NOW);

        verify(refreshTokens).deleteExpiredBefore(NOW);
        verify(resetTokens).deleteExpiredBefore(NOW);
        verify(emailChangeTokens).deleteExpiredBefore(NOW);
        verify(evidence).purgeBefore(NOW);
        assertThat(sweep.failed()).isEmpty();
    }

    @Test
    void theEvidenceWindowIsItsOwnKnobNotTheCredentialGrace() {
        props.getRetention().setRetiredDocumentDays(7);

        sweeper.sweep(NOW);

        // Two questions with two clocks: thirty days past a token's expiry and a week past a
        // document's retirement are different promises, and one operator moving one knob must
        // not move the other.
        verify(evidence).purgeBefore(NOW.minusDays(7));
        verify(refreshTokens).deleteExpiredBefore(NOW.minusDays(30));
    }

    @Test
    void thePurgeReportsTheRowsItDeletedAndTheChunksThatWentWithThem() {
        when(evidence.purgeBefore(NOW.minusDays(180)))
                .thenReturn(new RetiredEvidencePurger.Purge(2, 40, 0));

        RetentionSweeper.Sweep sweep = sweeper.sweep(NOW);

        // Chunks are the bulk of what a purge removes and they leave by the row's cascade, so
        // a reading that counted only documents would understate the night by the table that
        // actually grew fastest.
        assertThat(sweep.deleted()).containsEntry(RetentionSweeper.DOCUMENTS, 2L)
                .containsEntry(RetentionSweeper.DOCUMENT_CHUNKS, 40L);
        assertThat(count(RetentionSweeper.DOCUMENTS)).isEqualTo(2.0);
        assertThat(count(RetentionSweeper.DOCUMENT_CHUNKS)).isEqualTo(40.0);
        assertThat(sweep.failed()).isEmpty();
    }

    @Test
    void aRowThePurgeLeftBehindIsAnomalyNotFailure() {
        when(evidence.purgeBefore(NOW.minusDays(180)))
                .thenReturn(new RetiredEvidencePurger.Purge(2, 40, 3));

        RetentionSweeper.Sweep sweep = sweeper.sweep(NOW);

        // Three retired rows a source still names stayed, and the sweep did remove the other
        // two: a phase that skipped a row is not a phase that failed, so both readings move and
        // nothing lands in the failed list. The skip itself is the WARN line's business.
        assertThat(sweep.failed()).isEmpty();
        assertThat(sweep.deleted()).containsEntry(RetentionSweeper.DOCUMENTS, 2L);
    }

    @Test
    void aFailedPurgeNamesBothEvidenceTablesAndLeavesTheCredentialsSwept() {
        when(evidence.purgeBefore(NOW.minusDays(180)))
                .thenThrow(new IllegalStateException("deadlock on documents"));

        RetentionSweeper.Sweep sweep = sweeper.sweep(NOW);

        // Rows and chunks go in one statement, so a failed purge leaves neither count known --
        // and the credential deletes already committed in their own transactions.
        assertThat(sweep.failed()).containsExactly(
                RetentionSweeper.DOCUMENTS, RetentionSweeper.DOCUMENT_CHUNKS);
        assertThat(sweep.deleted()).doesNotContainKey(RetentionSweeper.DOCUMENTS)
                .doesNotContainKey(RetentionSweeper.DOCUMENT_CHUNKS);
        assertThat(counter(RetentionSweeper.DOCUMENTS)).isNull();
        assertThat(count(RetentionSweeper.REFRESH_TOKENS)).isEqualTo(3.0);
        assertThat(heartbeat()).isEqualTo(NOW.toEpochSecond());
    }

    private Counter counter(String table) {
        return registry.find(RetentionMetrics.DELETED).tag("table", table).counter();
    }

    private double count(String table) {
        Counter counter = counter(table);
        return counter == null ? 0.0 : counter.count();
    }
}
