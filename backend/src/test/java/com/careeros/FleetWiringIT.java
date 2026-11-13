package com.careeros;

import static org.assertj.core.api.Assertions.assertThat;

import com.careeros.auth.retention.RetentionScheduler;
import com.careeros.auth.retention.RetentionSweepHandler;
import com.careeros.job.service.IngestionScheduler;
import com.careeros.job.service.IngestionSweepHandler;
import com.careeros.queue.JobHandler;
import com.careeros.queue.JobQueue;
import com.careeros.queue.JobStream;
import com.careeros.queue.JobWorker;
import com.careeros.queue.RedisJobStream;
import com.careeros.report.service.WeeklyDigestComposeHandler;
import com.careeros.report.service.WeeklyDigestRetryHandler;
import com.careeros.report.service.WeeklyDigestScheduler;
import java.util.Map;
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

/**
 * The wiring the enablement sells — for real, end to end, inside the IT harness.
 *
 * <p>Against the suite's dedicated IT database and dedicated IT Redis (16399), with the queue
 * enabled: (1) every handler and scheduler composed in Epics 168–171 boots inside one
 * application context, and (2) one real entry flows producer → stream → consumer → registered
 * handler exactly once. This is the property the fleet story depends on and the one a unit
 * suite cannot prove: an unwired bean is a handler the fleet never finds — it exists as a
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
}
