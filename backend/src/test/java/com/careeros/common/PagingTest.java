package com.careeros.common;

import static com.careeros.common.Paging.MAX_PAGE_SIZE;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;
import org.springframework.data.domain.PageRequest;

/**
 * Pins the two halves of {@link Paging}: what the framework actually refuses, and what the
 * clamp hands back instead.
 */
class PagingTest {

    /**
     * The load-bearing half of this increment: without running a server, this is the proof
     * that the values a URL can carry were reaching a constructor that throws. If Spring ever
     * stops rejecting them, {@link Paging} is still correct — but this test says out loud
     * which behaviour the clamp was written against.
     */
    @Test
    void pageRequestItselfRejectsTheWindowsAUrlCanCarry() {
        assertThatThrownBy(() -> PageRequest.of(-1, 20))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("less than zero");
        assertThatThrownBy(() -> PageRequest.of(0, 0))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("less than one");
        assertThatThrownBy(() -> PageRequest.of(2, -5))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void aNegativePageBecomesTheFirstPage() {
        assertThat(Paging.of(-1, 20).page()).isZero();
        assertThat(Paging.of(-1, 20).offset()).isZero();
        assertThat(Paging.of(-1000, 20).page()).isZero();
        assertThat(Paging.of(0, 20).page()).isZero(); // 0 is a real answer, not a missing one
    }

    @Test
    void aWindowWithNoRowsStillAsksForRows() {
        assertThat(Paging.of(0, 0).size()).isEqualTo(1);
        assertThat(Paging.of(0, -5).size()).isEqualTo(1);
        // ?size= is dropped by the client, so Spring's default arrives here untouched
        assertThat(Paging.of(0, 20).size()).isEqualTo(20);
    }

    @Test
    void theCeilingLivesInTheWindowNotInTheCaller() {
        assertThat(Paging.of(0, 100_000).size()).isEqualTo(MAX_PAGE_SIZE);
        assertThat(Paging.of(0, MAX_PAGE_SIZE).size()).isEqualTo(MAX_PAGE_SIZE);
        assertThat(Paging.of(0, MAX_PAGE_SIZE + 1).size()).isEqualTo(MAX_PAGE_SIZE);
    }

    @Test
    void offsetIsTheClampedWindowNotTheRequestedOne() {
        assertThat(Paging.of(3, 50).offset()).isEqualTo(150L);
        assertThat(Paging.of(500, 100).offset()).isEqualTo(50_000L);
        assertThat(Paging.of(-4, 1_000_000).offset()).isZero();
        // The ceiling has to be applied *before* the multiplication. The line above
        // cannot tell the two orders apart — a floored page times out to zero either
        // way — so this one carries the ceiling half of the contract.
        assertThat(Paging.of(4, 1_000_000).offset()).isEqualTo(400L);
    }

    /** A huge page number is legal Spring Data input; only our own multiplication could break it. */
    @Test
    void aPageNumberPastTheIntProductStillYieldsASkippableOffset() {
        assertThat(Paging.of(2_000_000_000, 100).offset()).isEqualTo(200_000_000_000L);
        assertThat(Paging.of(Integer.MAX_VALUE, 100).offset()).isGreaterThan(0L);
        assertThat(Paging.of(Integer.MIN_VALUE, 100).offset()).isZero();
    }

    @Test
    void firstAsksForTheSameWindowZeroOffsetImplies() {
        assertThat(Paging.first(20)).isEqualTo(PageRequest.of(0, 20));
        assertThat(Paging.first(0).getPageSize()).isEqualTo(1);
        assertThat(Paging.first(10_000).getPageSize()).isEqualTo(MAX_PAGE_SIZE);
        assertThat(Paging.first(-5).getPageNumber()).isZero();
    }

    @Test
    void clampingIsIdempotentSoCallerAndCalleeCanBothDoIt() {
        Paging.Window once = Paging.of(-3, 0);
        assertThat(Paging.of(once.page(), once.size())).isEqualTo(once);
        Paging.Window capped = Paging.of(2, 10_000);
        assertThat(Paging.of(capped.page(), capped.size())).isEqualTo(capped);
    }

    @Test
    void everyWindowItProducesIsOneSpringAccepts() {
        int[] nasty = {Integer.MIN_VALUE, -1000, -1, 0, 1, 2, 20, 100, 101, 1_000_000};
        for (int page : nasty) {
            for (int size : nasty) {
                Paging.Window w = Paging.of(page, size);
                assertThatCode(() -> w.pageable()).doesNotThrowAnyException();
                assertThat(w.offset()).isGreaterThanOrEqualTo(0L);
            }
        }
    }
}
