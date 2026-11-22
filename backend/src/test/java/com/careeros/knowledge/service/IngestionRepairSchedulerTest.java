package com.careeros.knowledge.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.scheduling.annotation.Scheduled;

/**
 * The clock that rings Epic 418's pass (Epic 418).
 *
 * <p>Two things are worth pinning about a scheduler, and they are both about what it does not do:
 * it never rethrows, and it never decides. The pass owns the window, the claim and the limit; the
 * clock owns only the moment and the failure that must not end it.
 */
class IngestionRepairSchedulerTest {

    private IngestionRepairService repair;
    private IngestionRepairScheduler scheduler;

    @BeforeEach
    void setUp() {
        repair = mock(IngestionRepairService.class);
        scheduler = new IngestionRepairScheduler(repair);
    }

    @Test
    void aTickThatThrowsDoesNotStopTheClock() {
        // Spring cancels a fixedDelay task whose runnable escapes to the scheduler thread. The
        // database being unreachable is the failure most likely to hit the tick that exists to
        // notice trouble, so swallowing it is what keeps careeros_ingestion_repair_last_tick_timestamp
        // alive for the next window rather than stale for good.
        when(repair.sweep()).thenThrow(new IllegalStateException("database is unreachable"));

        assertThatCode(() -> scheduler.repairStuckIngestions()).doesNotThrowAnyException();

        verify(repair).sweep();
    }

    @Test
    void aTickThatFoundNothingIsStillATick() {
        when(repair.sweep()).thenReturn(0);

        scheduler.repairStuckIngestions();

        verify(repair).sweep();
    }

    @Test
    void theClockRingsOnTheKnobTheExampleDeclares() throws Exception {
        Scheduled scheduled = IngestionRepairScheduler.class
                .getDeclaredMethod("repairStuckIngestions")
                .getAnnotation(Scheduled.class);

        assertThat(scheduled.fixedDelayString())
                .isEqualTo("${careeros.ingestion.repair.interval-ms:600000}");
        assertThat(scheduled.initialDelayString())
                .as("no initial delay: a rolling deploy is how a document gets stranded, and the "
                        + "boot tick is what collects it")
                .isEmpty();
    }
}
