package com.careeros.job.service;

import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

import java.util.Map;
import org.junit.jupiter.api.Test;

/** The handler's one contract: one sweep per claimed entry, under the wire name the producer enqueues. */
class IngestionSweepHandlerTest {

    @Test
    void theKindIsTheWireNameTheQueueRoutesBy() {
        IngestionSweepHandler handler = new IngestionSweepHandler(mock(ScheduledIngestionService.class));
        org.assertj.core.api.Assertions.assertThat(handler.kind()).isEqualTo("ingestion.sweep");
    }

    @Test
    void handleRunsTheNightlySweepOnce() {
        ScheduledIngestionService ingestion = mock(ScheduledIngestionService.class);
        IngestionSweepHandler handler = new IngestionSweepHandler(ingestion);

        handler.handle(Map.of());

        verify(ingestion).sweepEnabled();
    }

    @Test
    void aFailedNightIsLoggedRatherThanThrownToTheWorkerLoop() {
        ScheduledIngestionService ingestion = mock(ScheduledIngestionService.class);
        org.mockito.Mockito.doThrow(new IllegalStateException("transport refused"))
                .when(ingestion).sweepEnabled();
        IngestionSweepHandler handler = new IngestionSweepHandler(ingestion);

        org.assertj.core.api.Assertions.assertThatCode(() -> handler.handle(Map.of()))
                .doesNotThrowAnyException();
    }
}
