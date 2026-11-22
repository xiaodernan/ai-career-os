package com.careeros;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.timeout;
import static org.mockito.Mockito.verify;

import com.careeros.ai.AiServiceClient;
import com.careeros.auth.retention.RetentionScheduler;
import com.careeros.auth.retention.RetentionSweepHandler;
import com.careeros.job.service.IngestionScheduler;
import com.careeros.job.service.IngestionSweepHandler;
import com.careeros.knowledge.service.RagCacheInvalidationJob;
import com.careeros.queue.JobHandler;
import com.careeros.queue.JobQueue;
import com.careeros.queue.JobStream;
import com.careeros.queue.JobWorker;
import com.careeros.queue.RedisJobStream;
import com.careeros.report.service.WeeklyDigestComposeHandler;
import com.careeros.report.service.WeeklyDigestRetryHandler;
import com.careeros.report.service.WeeklyDigestScheduler;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.ApplicationContext;
import org.springframework.context.annotation.Bean;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.test.context.bean.override.mockito.MockitoBean;

/**
 * The wiring the enablement sells — for real, end to end, inside the IT harness.
 *
 * <p>Against the suite's dedicated IT database and dedicated IT Redis (16399), with the queue
 * enabled: (1) every handler and scheduler composed in Epics 168–171 and 417 boots inside
 * one application context, (2) one real entry flows producer → stream → consumer → registered
 * handler exactly once, and (3) one entry of a kind the shipping code writes reaches the
 * handler that names that kind. This is the property the fleet story depends on and the one a
 * unit suite cannot prove: an unwired bean is a handler the fleet never finds — it exists as a
 * class, it never exists as a job.
 *
 * <p>Removed (both streams) before and after each run so a re-run starts empty. The IT
 * Redis serves this suite and no other; nothing here touches a deployment's data.
 */
@SpringBootTest(properties = {
        "careeros.queue.enabled=true",
        "careeros.queue.poll-ms=150",
        "careeros.queue.batch-size=10",
})
class FleetWiringIT extends AbstractIntegrationTest {

    /** A real registered handler with a real count of what reached it. */
    static class ProbeHandler implements JobHandler {
        static final AtomicInteger CALLS = new AtomicInteger();
        static final AtomicInteger SUITS = new AtomicInteger();

        @Override
        public String kind() {
            return "it.fleet.probe";
        }

        @Override
        public void handle(Map<String, String> payload) {
            CALLS.incrementAndGet();
            if ("fleet-wiring".equals(payload.get("suite"))) {
                SUITS.incrementAndGet();
            }
        }
    }

    @TestConfiguration
    static class ProbeConfig {
        @Bean
        ProbeHandler probeHandler() {
            return new ProbeHandler();
        }
    }

    @Autowired
    private StringRedisTemplate redis;

    @Autowired
    private ApplicationContext context;

    @Autowired
    private JobQueue queue;

    @Autowired
    private JobStream stream;

    @Autowired
    private JobWorker worker;

    @Autowired
    private ProbeHandler probe;

    /**
     * The HTTP boundary, replaced so this class can name the engine call a stream entry ends
     * in. The queue's own behaviour is the subject; whether an ai-service answers is Epic 147's
     * and is graded offline.
     */
    @MockitoBean
    private AiServiceClient ai;

    @BeforeEach
    void emptyTheStreamAndTheCounter() {
        ProbeHandler.CALLS.set(0);
        ProbeHandler.SUITS.set(0);
        redis.delete(RedisJobStream.STREAM);
        redis.delete(RedisJobStream.DEAD_STREAM);
    }

    @AfterEach
    void leaveNothingBehind() {
        redis.delete(RedisJobStream.STREAM);
        redis.delete(RedisJobStream.DEAD_STREAM);
    }

    @Test
    void everyComposedFleetHandlerAndSchedulerBootsInOneContext() {
        assertThat(queue.enabled()).isTrue();
        for (Class<?> bean : new Class<?>[] {
                RetentionSweepHandler.class,
                IngestionSweepHandler.class,
                WeeklyDigestComposeHandler.class,
                WeeklyDigestRetryHandler.class,
                RagCacheInvalidationJob.class,
                RetentionScheduler.class,
                IngestionScheduler.class,
                WeeklyDigestScheduler.class,
                JobWorker.class,
        }) {
            assertThat(context.getBean(bean))
                    .as("the context must hold %s; an unwired bean is a job the fleet never runs", bean)
                    .isNotNull();
        }
    }

    @Test
    void oneEntryChainsProducerToStreamToConsumerToHandlerExactlyOnce() throws Exception {
        assertThat(queue.enqueue("it.fleet.probe", Map.of("suite", "fleet-wiring"))).isTrue();

        for (int i = 0; i < 40 && ProbeHandler.CALLS.get() == 0; i++) {
            Thread.sleep(100);
        }

        assertThat(ProbeHandler.CALLS.get()).isEqualTo(1);
        assertThat(ProbeHandler.SUITS.get()).isEqualTo(1);
        assertThat(stream.pending(10)).isEmpty();
    }

    @Test
    void aRealEnqueuedJobReachesTheHandlerThatNamesItsKind() throws Exception {
        // The probe above proves the mechanics with a test's own handler. This one proves the
        // thing Epic 417 actually changed: the kind a production call site writes is the kind
        // a registered handler claims, and the field it writes is read back as the user it
        // names. A typo in either string is invisible to every unit test on both sides -- the
        // producer would enqueue, the worker would find no handler, and the entry would simply
        // stop being anyone's job.
        UUID owner = UUID.randomUUID();
        assertThat(queue.enqueue(RagCacheInvalidationJob.KIND,
                Map.of(RagCacheInvalidationJob.USER_FIELD, owner.toString()))).isTrue();

        verify(ai, timeout(8000)).invalidateCache(owner);

        // Two witnesses that this was a claimed job and not a discarded one: the dead-letter
        // stream was never created (that is where an entry no handler claims lands), and the
        // entry left the pending list, which only an ack does.
        assertThat(redis.hasKey(RedisJobStream.DEAD_STREAM)).isFalse();
        assertThat(stream.pending(100)).isEmpty();
    }
}
