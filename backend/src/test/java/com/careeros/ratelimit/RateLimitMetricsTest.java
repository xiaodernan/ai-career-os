package com.careeros.ratelimit;

import static org.assertj.core.api.Assertions.assertThat;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.Test;

class RateLimitMetricsTest {

    private final SimpleMeterRegistry registry = new SimpleMeterRegistry();
    private final RateLimitMetrics metrics = new RateLimitMetrics(registry);

    @Test
    void everyDecisionMovesTheCounterTaggedWithBucketAndOutcome() {
        metrics.record(RateLimitFilter.MAIL, false);
        metrics.record(RateLimitFilter.MAIL, false);
        metrics.record(RateLimitFilter.AI, true);

        assertThat(count(RateLimitFilter.MAIL, RateLimitMetrics.DENIED)).isEqualTo(2.0);
        assertThat(count(RateLimitFilter.AI, RateLimitMetrics.ALLOWED)).isEqualTo(1.0);
        assertThat(count(RateLimitFilter.AI, RateLimitMetrics.DENIED)).isZero();
    }

    @Test
    void allowedAndDeniedAreSeparateSeriesForTheSameBucket() {
        metrics.record(RateLimitFilter.AUTH, true);
        metrics.record(RateLimitFilter.AUTH, false);

        assertThat(count(RateLimitFilter.AUTH, RateLimitMetrics.ALLOWED)).isEqualTo(1.0);
        assertThat(count(RateLimitFilter.AUTH, RateLimitMetrics.DENIED)).isEqualTo(1.0);
    }

    @Test
    void aBucketExportsNothingUntilItsFirstDecision() {
        assertThat(registry.find(RateLimitMetrics.DECISIONS).counters()).isEmpty();

        metrics.record(RateLimitFilter.AI, true);

        assertThat(registry.find(RateLimitMetrics.DECISIONS).counters()).hasSize(1);
    }

    private double count(String bucket, String outcome) {
        Counter counter = registry.find(RateLimitMetrics.DECISIONS)
                .tag("bucket", bucket)
                .tag("outcome", outcome)
                .counter();
        return counter == null ? 0.0 : counter.count();
    }
}
