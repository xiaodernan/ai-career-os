package com.careeros.auth.retention;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

import java.time.OffsetDateTime;
import java.util.Map;
import org.junit.jupiter.api.Test;

/**
 * The handler's one contract: the sweep runs exactly once per claimed entry, under the
 * wire name the producer enqueues and the fleet queue routes by.
 */
class RetentionSweepHandlerTest {

    @Test
    void theKindIsTheWireNameTheQueueRoutesBy() {
        RetentionSweepHandler handler = new RetentionSweepHandler(mock(RetentionSweeper.class));
        assertThat(handler.kind()).isEqualTo("retention.sweep");
    }

    @Test
    void handleRunsTheSweepOnce() {
        RetentionSweeper sweeper = mock(RetentionSweeper.class);
        RetentionSweepHandler handler = new RetentionSweepHandler(sweeper);

        handler.handle(Map.of());

        org.mockito.ArgumentCaptor<OffsetDateTime> captor =
                org.mockito.ArgumentCaptor.forClass(OffsetDateTime.class);
        verify(sweeper).sweep(captor.capture());
        assertThat(captor.getValue().toInstant().getEpochSecond())
                .isGreaterThan(OffsetDateTime.now().minusMinutes(1).toInstant().getEpochSecond());
    }
}
