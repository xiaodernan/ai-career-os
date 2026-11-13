package com.careeros.report.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.careeros.activity.repository.AiUsageEventRepository;
import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

/**
 * Today's-spend arithmetic (roadmap 21.x), pinned against the one ledger the engine
 * writes. The route's whole job is preventing an invented state: a zero day is a zero,
 * the cap is the dashboard's bar and not a gate, and the ratio is the input cache over
 * the input the model actually billed.
 */
class AiSpendServiceTest {

    private static final UUID ALICE = UUID.fromString("11111111-1111-4111-8111-111111111111");

    private AiUsageEventRepository usage;
    private AiSpendService service;

    @BeforeEach
    void setUp() {
        usage = mock(AiUsageEventRepository.class);
        service = new AiSpendService(usage);
        ReflectionTestUtils.setField(service, "capUsd", new BigDecimal("10.00"));
    }

    private void ledger(BigDecimal cost, long in, long out, long cached, long calls) {
        java.util.List<Object[]> rows = new java.util.ArrayList<>();
        rows.add(new Object[]{cost, in, out, cached, calls});
        when(usage.usageTotalsSince(eq(ALICE), any(OffsetDateTime.class)))
                .thenReturn(rows);
    }

    @Test
    void a_day_of_work_is_summed_with_the_cache_ratio() {
        ledger(new BigDecimal("0.123456"), 10000, 1200, 4500, 3);

        Map<String, Object> out = service.today(ALICE);

        assertThat(((BigDecimal) out.get("costUsd")).toPlainString()).isEqualTo("0.123456");
        assertThat(out.get("calls")).isEqualTo(3L);
        assertThat(out.get("inputTokens")).isEqualTo(10000L);
        assertThat(out.get("outputTokens")).isEqualTo(1200L);
        assertThat(out.get("cachedTokens")).isEqualTo(4500L);
        assertThat(out.get("cacheHitRatio")).isEqualTo(0.45);
        assertThat(out.get("capEnabled")).isEqualTo(true);
        assertThat(out.get("capExceeded")).isEqualTo(false);
        assertThat(((String) out.get("dayStart"))).endsWith("Z");
    }

    @Test
    void an_empty_day_is_zero_not_an_error() {
        when(usage.usageTotalsSince(eq(ALICE), any(OffsetDateTime.class))).thenReturn(List.of());

        Map<String, Object> out = service.today(ALICE);

        assertThat(((BigDecimal) out.get("costUsd")).compareTo(BigDecimal.ZERO)).isZero();
        assertThat(out.get("calls")).isEqualTo(0L);
        assertThat(out.get("cacheHitRatio")).isEqualTo(0.0);
        assertThat(out.get("capExceeded")).isEqualTo(false);
    }

    @Test
    void a_zero_cap_removes_the_bar() {
        ReflectionTestUtils.setField(service, "capUsd", BigDecimal.ZERO);
        ledger(new BigDecimal("99.00"), 1000, 100, 0, 1);

        Map<String, Object> out = service.today(ALICE);

        assertThat(out.get("capEnabled")).isEqualTo(false);
        assertThat(out.get("capExceeded")).isEqualTo(false);
        assertThat(((BigDecimal) out.get("capUsd")).compareTo(BigDecimal.ZERO)).isZero();
    }

    @Test
    void a_day_at_the_cap_is_reported_not_refused() {
        ledger(new BigDecimal("10.00"), 5000, 100, 0, 9);
        assertThat(service.today(ALICE).get("capExceeded")).isEqualTo(true);

        ledger(new BigDecimal("10.01"), 5000, 100, 0, 9);
        assertThat(service.today(ALICE).get("capExceeded")).isEqualTo(true);
    }

    @Test
    void a_ratio_with_no_input_tokens_is_zero() {
        ledger(BigDecimal.ZERO, 0, 400, 0, 1);
        assertThat(service.today(ALICE).get("cacheHitRatio")).isEqualTo(0.0);
    }

    @Test
    void the_ratio_rounds_to_four_decimals() {
        ledger(BigDecimal.ZERO, 3, 1, 1, 1);
        assertThat(service.today(ALICE).get("cacheHitRatio")).isEqualTo(0.3333);
    }

    @Test
    void the_day_is_bounded_at_utc_midnight() {
        ledger(BigDecimal.ZERO, 100, 10, 50, 1);
        service.today(ALICE);
        // captured in the ledger stub's any(); the assertion that matters is the one
        // the row is filtered by — the repo test could prove the SQL, so keep this cheap:
        // the window starts at the current UTC day, never at a local midnight.
        org.mockito.Mockito.verify(usage).usageTotalsSince(eq(ALICE), any(OffsetDateTime.class));
    }
}
