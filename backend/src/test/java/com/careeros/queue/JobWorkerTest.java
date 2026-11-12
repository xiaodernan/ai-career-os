package com.careeros.queue;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

/**
 * The consumer's policy, driven over an in-memory group so a crashed replica is a state a test
 * can write down rather than a process it has to kill.
 *
 * <p>Four claims are worth a suite: a job is acknowledged <em>only</em> when its handler
 * finished; a failure leaves the job where a sibling can find it; an entry that has had its
 * last attempt is recorded and retired instead of retried forever; and a disabled worker sends
 * no command at all. The attempt bound is pinned from both sides (one attempt left still runs,
 * no attempts left does not), because an off-by-one there either loses a retry or burns a
 * worker on a poison job -- the two failures this queue exists to prevent.
 */
class JobWorkerTest {

    private static final String KIND = "test.job";

    private final SimpleMeterRegistry registry = new SimpleMeterRegistry();
    private final QueueMetrics metrics = new QueueMetrics(registry);
    private final FakeJobStream stream = new FakeJobStream();
    private final RecordingHandler handler = new RecordingHandler();

    private static final class RecordingHandler implements JobHandler {
        final List<Map<String, String>> calls = new ArrayList<>();
        RuntimeException failure;

        @Override
        public String kind() {
            return KIND;
        }

        @Override
        public void handle(Map<String, String> payload) {
            calls.add(new LinkedHashMap<>(payload));
            if (failure != null) {
                throw failure;
            }
        }
    }

    private JobWorker worker(boolean enabled, JobHandler... handlers) {
        return new JobWorker(stream, new JobQueue(stream, metrics, enabled), metrics,
                List.of(handlers), 20, 5, 30_000);
    }

    private double counted(String kind, String outcome) {
        var counter = registry.find(QueueMetrics.JOBS).tag("kind", kind).tag("outcome", outcome).counter();
        return counter == null ? 0 : counter.count();
    }

    private Map<String, String> job(String userId) {
        return Map.of(JobQueue.KIND_FIELD, KIND, "userId", userId);
    }

    @Test
    void a_disabled_worker_sends_no_command() {
        stream.add(job("u1"));
        stream.resetCounters();

        worker(false, handler).tick();

        assertThat(stream.commands()).isZero();
        assertThat(handler.calls).isEmpty();
        assertThat(stream.pel).isEmpty();
        assertThat(registry.find(QueueMetrics.JOBS).counters()).isEmpty();
    }

    @Test
    void a_finished_job_is_acknowledged_and_its_payload_loses_the_routing_field() {
        stream.add(job("u1"));

        worker(true, handler).tick();

        assertThat(handler.calls).containsExactly(Map.of("userId", "u1"));
        assertThat(stream.pel).isEmpty();
        assertThat(stream.acks).isEqualTo(1);
        assertThat(counted(KIND, "done")).isEqualTo(1);
        assertThat(stream.groupCreated).isTrue();
    }

    @Test
    void a_failed_job_stays_pending_for_a_sibling_and_is_not_counted_done() {
        String id = stream.add(job("u1"));
        handler.failure = new IllegalStateException("the engine refused");

        worker(true, handler).tick();

        assertThat(handler.calls).hasSize(1);
        assertThat(stream.pel).containsKey(id);
        assertThat(stream.acks).isZero();
        assertThat(counted(KIND, "failed")).isEqualTo(1);
        assertThat(counted(KIND, "done")).isZero();
    }

    @Test
    void an_entry_nobody_claims_is_dead_lettered_rather_than_retried_forever() {
        String id = stream.add(Map.of(JobQueue.KIND_FIELD, "a.kind.no.handler.names"));

        worker(true, handler).tick();

        assertThat(handler.calls).isEmpty();
        assertThat(stream.pel).doesNotContainKey(id);
        assertThat(stream.dead).hasSize(1);
        assertThat(stream.dead.get(0))
                .containsEntry("reason", "no-handler")
                .containsEntry("from", id)
                .containsEntry(JobQueue.KIND_FIELD, "a.kind.no.handler.names");
        // The tag is the registry's word, not the wire's: a bad payload cannot mint a series.
        assertThat(counted("unknown", "dead")).isEqualTo(1);
    }

    @Test
    void a_crashed_replicas_job_is_reclaimed_and_run_by_its_sibling() {
        String id = stream.strand("9999@dead-replica", job("u1"), 1);
        stream.advance(Duration.ofSeconds(60));

        JobWorker worker = worker(true, handler);
        worker.tick();

        assertThat(handler.calls).containsExactly(Map.of("userId", "u1"));
        assertThat(stream.pel).doesNotContainKey(id);
        assertThat(counted(KIND, "reclaimed")).isEqualTo(1);
        assertThat(counted(KIND, "done")).isEqualTo(1);
        assertThat(worker.consumerName()).isNotBlank().isNotEqualTo("9999@dead-replica");
    }

    @Test
    void a_slow_siblings_fresh_work_is_not_stolen() {
        String id = stream.strand("9999@slow-replica", job("u1"), 1);

        worker(true, handler).tick();

        assertThat(stream.claims).isZero();
        assertThat(handler.calls).isEmpty();
        assertThat(stream.pel).containsKey(id);
    }

    @Test
    void an_entry_that_has_had_its_last_attempt_is_recorded_and_retired() {
        String id = stream.strand("9999@dead-replica", job("u1"), 5);
        stream.advance(Duration.ofSeconds(60));

        worker(true, handler).tick();

        assertThat(handler.calls).isEmpty();
        assertThat(stream.pel).doesNotContainKey(id);
        assertThat(stream.dead).hasSize(1);
        assertThat(stream.dead.get(0))
                .containsEntry("reason", "max-deliveries")
                .containsEntry("userId", "u1")
                .containsEntry("from", id);
        assertThat(counted(KIND, "dead")).isEqualTo(1);
        assertThat(counted(KIND, "reclaimed")).isZero();
    }

    @Test
    void one_attempt_left_is_still_an_attempt() {
        stream.strand("9999@dead-replica", job("u1"), 4);
        stream.advance(Duration.ofSeconds(60));

        worker(true, handler).tick();

        assertThat(handler.calls).hasSize(1);
        assertThat(stream.dead).isEmpty();
        assertThat(counted(KIND, "done")).isEqualTo(1);
    }

    @Test
    void a_tick_is_bounded_by_its_batch_on_both_the_new_and_the_reclaimed_side() {
        for (int i = 0; i < 50; i++) {
            stream.strand("9999@dead-replica", job("u" + i), 1);
        }
        stream.advance(Duration.ofSeconds(60));

        worker(true, handler).tick();

        assertThat(handler.calls).hasSize(20);
        assertThat(stream.pel).hasSize(30);
    }

    @Test
    void a_dead_letter_write_that_fails_does_not_acknowledge_the_job() {
        String id = stream.strand("9999@dead-replica", job("u1"), 5);
        stream.advance(Duration.ofSeconds(60));
        stream.deadFailure = new IllegalStateException("READONLY");

        assertThatCode(() -> worker(true, handler).tick()).doesNotThrowAnyException();

        // Losing the record of a dropped job must not also lose the job.
        assertThat(stream.pel).containsKey(id);
        assertThat(stream.acks).isZero();
        assertThat(stream.dead).isEmpty();
    }

    @Test
    void a_tick_that_cannot_reach_redis_keeps_the_work_and_tries_again() {
        stream.add(job("u1"));
        stream.readFailure = new IllegalStateException("connection refused");

        assertThatCode(() -> worker(true, handler).tick()).doesNotThrowAnyException();
        assertThat(handler.calls).isEmpty();

        stream.readFailure = null;
        worker(true, handler).tick();

        assertThat(handler.calls).hasSize(1);
    }

    @Test
    void a_group_that_cannot_be_created_yet_is_retried_on_the_next_tick() {
        stream.add(job("u1"));
        stream.groupFailure = new IllegalStateException("connection refused");
        JobWorker worker = worker(true, handler);

        worker.tick();
        assertThat(stream.groupCreated).isFalse();
        assertThat(stream.reads).isZero();

        stream.groupFailure = null;
        worker.tick();

        assertThat(stream.groupCreated).isTrue();
        assertThat(handler.calls).hasSize(1);
    }

    @Test
    void an_acknowledgement_that_fails_is_not_reported_as_a_finished_job() {
        String id = stream.add(job("u1"));
        stream.ackFailure = new IllegalStateException("connection refused");

        assertThatCode(() -> worker(true, handler).tick()).doesNotThrowAnyException();

        assertThat(handler.calls).hasSize(1);
        assertThat(counted(KIND, "done")).isZero();
        assertThat(counted(KIND, "failed")).isZero();
        // The job ran but is still pending: the handler's idempotence is what makes that safe.
        assertThat(stream.pel).containsKey(id);
    }

    @Test
    void two_handlers_claiming_one_kind_refuse_to_start() {
        assertThatThrownBy(() -> worker(true, handler, new RecordingHandler()))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining(KIND);
    }

    @Test
    void an_empty_tick_creates_the_group_once_and_reads_no_work() {
        JobWorker worker = worker(true, handler);

        worker.tick();
        worker.tick();

        assertThat(stream.groups).isEqualTo(1);
        assertThat(stream.reads).isEqualTo(2);
        assertThat(handler.calls).isEmpty();
    }
}