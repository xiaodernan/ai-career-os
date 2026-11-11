package com.careeros.common;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import jakarta.servlet.FilterChain;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.time.Instant;
import org.junit.jupiter.api.Test;

/**
 * Epic 128, pinned: the deadline a caller carries is visible on the thread that
 * serves the request and cleared when the request leaves; a malformed value is
 * ignored rather than refused; a past-due deadline reads as expired. The AI bridge
 * refuses before dispatch on this reading, so a wrong answer here is engine work
 * nobody waits for.
 */
class DeadlineFilterTest {

    private final DeadlineFilter filter = new DeadlineFilter();

    private void run(String header, java.util.concurrent.atomic.AtomicReference<Long> seen,
                    java.util.concurrent.atomic.AtomicBoolean expiredSeen) throws Exception {
        HttpServletRequest request = mock(HttpServletRequest.class);
        if (header != null) {
            when(request.getHeader(DeadlineFilter.HEADER)).thenReturn(header);
        }
        HttpServletResponse response = mock(HttpServletResponse.class);
        FilterChain chain = mock(FilterChain.class);
        doAnswer(invocation -> {
            seen.set(DeadlineFilter.current());
            expiredSeen.set(DeadlineFilter.expired());
            return null;
        }).when(chain).doFilter(any(), any());

        filter.doFilterInternal(request, response, chain);
    }

    @Test
    void aFutureDeadlineIsCarriedThroughAndNotExpired() throws Exception {
        long future = Instant.now().plusSeconds(600).toEpochMilli();
        var seen = new java.util.concurrent.atomic.AtomicReference<Long>();
        var expired = new java.util.concurrent.atomic.AtomicBoolean();

        run(String.valueOf(future), seen, expired);

        assertThat(seen.get()).isEqualTo(future);
        assertThat(expired.get()).isFalse();
        // Cleared on the way out: a pooled thread does not leak one request's budget.
        assertThat(DeadlineFilter.current()).isNull();
    }

    @Test
    void aPastDeadlineReadsAsExpiredInsideTheChain() throws Exception {
        long past = Instant.now().minusSeconds(1).toEpochMilli();
        var seen = new java.util.concurrent.atomic.AtomicReference<Long>();
        var expired = new java.util.concurrent.atomic.AtomicBoolean();

        run(String.valueOf(past), seen, expired);

        assertThat(seen.get()).isEqualTo(past);
        assertThat(expired.get()).isTrue();
        assertThat(DeadlineFilter.current()).isNull();
    }

    @Test
    void garbageIsIgnoredNotRefused() throws Exception {
        for (String garbage : new String[]{"", "tomorrow", "12.5", "1e9", "-100", "abc123", "9".repeat(16)}) {
            var seen = new java.util.concurrent.atomic.AtomicReference<Long>();
            var expired = new java.util.concurrent.atomic.AtomicBoolean();

            run(garbage, seen, expired);

            assertThat(seen.get()).as("garbage %r must not become a budget", garbage).isNull();
            assertThat(expired.get()).isFalse();
        }
    }

    @Test
    void noHeaderMeansNoBudgetAndNoExpiry() throws Exception {
        var seen = new java.util.concurrent.atomic.AtomicReference<Long>();
        var expired = new java.util.concurrent.atomic.AtomicBoolean(true);

        run(null, seen, expired);

        assertThat(seen.get()).isNull();
        assertThat(expired.get()).isFalse();
    }
}
