package com.careeros.queue;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyMap;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.util.LinkedHashMap;
import java.util.Map;
import org.junit.jupiter.api.Test;

/**
 * The producer's contract, and the one property that makes the queue safe to add to a running
 * product: <b>off is off</b>. A disabled queue must send no Redis command and register no
 * series, so a checkout that never asked for a queue behaves byte-for-byte as it did before
 * the queue existed. The other half is the failure boundary -- a Redis that refuses the write
 * answers false rather than throwing, because the caller is a delete that already committed.
 */
class JobQueueTest {

    private final SimpleMeterRegistry registry = new SimpleMeterRegistry();
    private final QueueMetrics metrics = new QueueMetrics(registry);

    private double counted(String kind, String outcome) {
        var counter = registry.find(QueueMetrics.JOBS).tag("kind", kind).tag("outcome", outcome).counter();
        return counter == null ? 0 : counter.count();
    }

    @Test
    void a_disabled_queue_sends_no_command_and_registers_no_series() {
        JobStream stream = mock(JobStream.class);
        JobQueue queue = new JobQueue(stream, metrics, false);

        assertThat(queue.enabled()).isFalse();
        assertThat(queue.enqueue("test.job", Map.of("userId", "u1"))).isFalse();

        verifyNoInteractions(stream);
        assertThat(registry.find(QueueMetrics.JOBS).counters()).isEmpty();
    }

    @Test
    void an_enabled_queue_writes_the_routing_kind_beside_the_payload() {
        FakeJobStream stream = new FakeJobStream();
        JobQueue queue = new JobQueue(stream, metrics, true);

        assertThat(queue.enqueue("test.job", Map.of("userId", "u1"))).isTrue();

        assertThat(stream.entries).hasSize(1);
        assertThat(stream.entries.values().iterator().next())
                .containsEntry(JobQueue.KIND_FIELD, "test.job")
                .containsEntry("userId", "u1");
        assertThat(counted("test.job", "enqueued")).isEqualTo(1);
    }

    @Test
    void a_refused_write_is_a_false_answer_not_an_exception() {
        FakeJobStream stream = new FakeJobStream();
        stream.addFailure = new IllegalStateException("READONLY You can't write against a read only replica");
        JobQueue queue = new JobQueue(stream, metrics, true);

        assertThat(queue.enqueue("test.job", Map.of("userId", "u1"))).isFalse();

        assertThat(stream.entries).isEmpty();
        assertThat(counted("test.job", "dropped")).isEqualTo(1);
        assertThat(counted("test.job", "enqueued")).isZero();
    }

    @Test
    void the_producers_own_map_is_not_mutated() {
        FakeJobStream stream = new FakeJobStream();
        JobQueue queue = new JobQueue(stream, metrics, true);
        Map<String, String> payload = new LinkedHashMap<>(Map.of("userId", "u1"));

        queue.enqueue("test.job", payload);

        assertThat(payload).containsOnlyKeys("userId");
    }

    @Test
    void the_routing_kind_wins_over_a_payload_field_of_the_same_name() {
        FakeJobStream stream = new FakeJobStream();
        JobQueue queue = new JobQueue(stream, metrics, true);

        queue.enqueue("test.job", Map.of(JobQueue.KIND_FIELD, "something.else"));

        assertThat(stream.entries.values().iterator().next())
                .containsEntry(JobQueue.KIND_FIELD, "test.job");
    }

    @Test
    void an_empty_payload_is_a_job_that_carries_only_its_kind() {
        JobStream stream = mock(JobStream.class);
        when(stream.add(anyMap())).thenReturn("1-0");
        JobQueue queue = new JobQueue(stream, metrics, true);

        assertThat(queue.enqueue("test.job", new LinkedHashMap<>())).isTrue();
    }
}