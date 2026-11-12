package com.careeros;

import static org.assertj.core.api.Assertions.assertThat;

import com.careeros.queue.JobHandler;
import com.careeros.queue.JobQueue;
import com.careeros.queue.JobStream.Entry;
import com.careeros.queue.JobStream.Pending;
import com.careeros.queue.JobWorker;
import com.careeros.queue.QueueMetrics;
import com.careeros.queue.RedisJobStream;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.time.Duration;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Range;
import org.springframework.data.redis.connection.stream.MapRecord;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;

/**
 * The queue against a real Redis, because three of its claims are the server's behaviour and
 * not the policy's: a group hands an entry to one consumer, XCLAIM re-checks the idle time so a
 * live consumer keeps its work, and MAXLEN bounds the stream at the write. A fake can agree with
 * all three and still be wrong about the server; this suite is where the transport earns them.
 *
 * <p>The last case is the whole point of the epic end to end: a handler that always fails is
 * retried up to its delivery bound and then recorded on the dead-letter stream, with the real
 * PEL -- not a test's map -- as the witness that it stopped being pending.
 *
 * <p>Runs on the suite's dedicated {@code careeros-it-redis} (16399), never the dev server, and
 * removes its own two keys before and after so a re-run starts from an empty group.
 */
class JobQueueIT extends AbstractIntegrationTest {

    /**
     * The bounding case storms the stream with 300 individual XADDs over the suite's dev proxy,
     * and the default 500 ms command window is meant to fail fast in production, not to gate a
     * bulk-write loop on a shared Docker Desktop box. Five seconds for this class only; the
     * production default is untouched, and no other suite's timeout moves.
     */
    @DynamicPropertySource
    static void commandTimeout(DynamicPropertyRegistry registry) {
        registry.add("spring.data.redis.timeout", () -> "5s");
    }

    @Autowired
    private StringRedisTemplate redis;

    private final SimpleMeterRegistry registry = new SimpleMeterRegistry();
    private QueueMetrics metrics;
    private RedisJobStream stream;

    @BeforeEach
    void emptyTheStreams() {
        metrics = new QueueMetrics(registry);
        stream = new RedisJobStream(redis, 10_000);
        redis.delete(RedisJobStream.STREAM);
        redis.delete(RedisJobStream.DEAD_STREAM);
    }

    @AfterEach
    void leaveNothingBehind() {
        redis.delete(RedisJobStream.STREAM);
        redis.delete(RedisJobStream.DEAD_STREAM);
    }

    @Test
    void a_group_hands_each_entry_to_exactly_one_consumer() {
        stream.ensureGroup();
        for (int i = 0; i < 10; i++) {
            stream.add(Map.of("kind", "test.job", "n", String.valueOf(i)));
        }

        // Redis does not split a batch across two callers of `>`: the read offers the whole
        // un-delivered queue to the consumer that asked, capped by `count`, so a bulk read by
        // one replica legitimately returns every entry while a bulk read by the next returns
        // none. What a group *does* guarantee is that no entry reaches two consumers, and an
        // entry already delivered stays with the replica that got it. Alternating unit reads --
        // the interleaving a real fleet produces -- make both replicas progress and prove
        // exclusivity at the same time.
        List<Entry> a = new ArrayList<>();
        List<Entry> b = new ArrayList<>();
        for (int i = 0; i < 5; i++) {
            List<Entry> ra = stream.read("replica-a", 1);
            List<Entry> rb = stream.read("replica-b", 1);
            assertThat(ra).hasSize(1);
            assertThat(rb).hasSize(1);
            a.addAll(ra);
            b.addAll(rb);
        }

        List<Entry> first = a;
        List<Entry> second = b;
        Set<String> ids = new HashSet<>();
        first.forEach(entry -> ids.add(entry.id()));
        second.forEach(entry -> ids.add(entry.id()));
        assertThat(first).isNotEmpty();
        assertThat(second).isNotEmpty();
        assertThat(ids).hasSize(10);
        assertThat(stream.pending(100)).hasSize(10);
    }

    @Test
    void a_fresh_entry_is_not_stolen_but_an_idle_one_is_reclaimed_with_one_more_delivery() {
        stream.ensureGroup();
        String id = stream.add(Map.of("kind", "test.job", "userId", "u1"));
        stream.read("replica-a", 1);

        // The server re-checks the idle time inside XCLAIM: a consumer that just took the job
        // keeps it, which is what stops two replicas running the same work at the same time.
        assertThat(stream.claim("replica-b", Duration.ofMillis(500), List.of(id))).isEmpty();

        sleep(600);
        List<Entry> claimed = stream.claim("replica-b", Duration.ofMillis(500), List.of(id));

        assertThat(claimed).hasSize(1);
        assertThat(claimed.get(0).fields()).containsEntry("userId", "u1");
        List<Pending> pending = stream.pending(10);
        assertThat(pending).hasSize(1);
        assertThat(pending.get(0).consumer()).isEqualTo("replica-b");
        assertThat(pending.get(0).deliveries()).isEqualTo(2);
    }

    @Test
    void an_acknowledged_entry_leaves_the_pending_list() {
        stream.ensureGroup();
        String id = stream.add(Map.of("kind", "test.job"));
        stream.read("replica-a", 1);
        assertThat(stream.pending(10)).hasSize(1);

        stream.ack(id);

        assertThat(stream.pending(10)).isEmpty();
    }

    @Test
    void the_stream_stops_growing_with_the_producer() {
        RedisJobStream bounded = new RedisJobStream(redis, 50);
        bounded.ensureGroup();

        for (int i = 0; i < 300; i++) {
            bounded.add(Map.of("kind", "test.job", "n", String.valueOf(i)));
        }

        Long size = redis.opsForStream().size(RedisJobStream.STREAM);
        assertThat(size).isNotNull();
        // Approximate trimming (`MAXLEN ~`) lets Redis keep whole radix nodes, so the bound is
        // a ceiling with slack, not an exact count -- but 300 writes must not mean 300 entries.
        assertThat(size).isLessThanOrEqualTo(100);
    }

    @Test
    void a_job_that_always_fails_is_retried_to_its_bound_and_then_dead_lettered() {
        List<Map<String, String>> attempts = new ArrayList<>();
        JobHandler alwaysFails = new JobHandler() {
            @Override
            public String kind() {
                return "test.job";
            }

            @Override
            public void handle(Map<String, String> payload) {
                attempts.add(payload);
                throw new IllegalStateException("the engine refused");
            }
        };
        JobQueue queue = new JobQueue(stream, metrics, true);
        JobWorker worker = new JobWorker(stream, queue, metrics, List.of(alwaysFails), 20, 2, 1);

        assertThat(queue.enqueue("test.job", Map.of("userId", "u1"))).isTrue();

        worker.tick();          // attempt 1: read, fail, left pending
        sleep(5);
        worker.tick();          // attempt 2: reclaimed (1 delivery so far), fail, left pending
        sleep(5);
        worker.tick();          // 2 deliveries so far == the bound: recorded and retired

        assertThat(attempts).hasSize(2);
        assertThat(stream.pending(10)).isEmpty();
        List<MapRecord<String, Object, Object>> dead = deadRecords();
        assertThat(dead).hasSize(1);
        assertThat(dead.get(0).getValue())
                .containsEntry("reason", "max-deliveries")
                .containsEntry("userId", "u1")
                .containsEntry("kind", "test.job");
        assertThat(registry.find(QueueMetrics.JOBS).tag("kind", "test.job").tag("outcome", "dead").counter().count())
                .isEqualTo(1);
        assertThat(registry.find(QueueMetrics.JOBS).tag("kind", "test.job").tag("outcome", "failed").counter().count())
                .isEqualTo(2);
    }

    /** The dead-letter stream's raw records, so the assertion reads what an operator would. */
    private List<MapRecord<String, Object, Object>> deadRecords() {
        List<MapRecord<String, Object, Object>> records =
                redis.opsForStream().range(RedisJobStream.DEAD_STREAM, Range.unbounded());
        return records == null ? List.of() : records;
    }

    private static void sleep(long millis) {
        try {
            Thread.sleep(millis);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException(e);
        }
    }
}