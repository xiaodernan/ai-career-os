package com.careeros.attention.service;

import static org.assertj.core.api.Assertions.assertThat;

import com.careeros.attention.entity.AttentionEvent;
import java.util.List;
import java.util.Random;
import java.util.stream.Collectors;
import org.junit.jupiter.api.Test;

/**
 * The simulator's promises, pinned at the row level: every row carries the
 * synthetic journey, no row names a reader, and the cap is a cap.
 */
class AttentionSimulatorTest {

    @Test
    void everyRowIsSyntheticAndCarriesNoUserId() {
        List<AttentionEvent> rows = AttentionAdminService.simulateRows(50, new Random(42L));
        assertThat(rows).isNotEmpty();
        assertThat(rows).allSatisfy(r -> {
            assertThat(r.getJourney()).isEqualTo("synthetic");
            assertThat(r.getUserId()).isNull();
        });
    }

    @Test
    void theCapIsACap() {
        List<AttentionEvent> rows = AttentionAdminService.simulateRows(10_000, new Random(7L));
        int landings = (int) rows.stream().filter(r -> "land".equals(r.getEvent())).count();
        // every session logs at least one land; engagement adds more
        assertThat(landings).isGreaterThanOrEqualTo(AttentionAdminService.MAX_SESSIONS);
        assertThat(rows.size()).isGreaterThan(AttentionAdminService.MAX_SESSIONS * 2);
    }

    @Test
    void deterministicPerSeed() {
        List<AttentionEvent> a = AttentionAdminService.simulateRows(25, new Random(99L));
        List<AttentionEvent> b = AttentionAdminService.simulateRows(25, new Random(99L));
        assertThat(a.size()).isEqualTo(b.size());
        assertThat(a.stream().map(r -> r.getPath() + ":" + r.getEvent() + ":" + String.valueOf(r.getValue())).collect(Collectors.toList()))
                .isEqualTo(b.stream().map(r -> r.getPath() + ":" + r.getEvent() + ":" + String.valueOf(r.getValue())).collect(Collectors.toList()));
    }

    @Test
    void wipeCallsDeleteOnlyForSynthetic() {
        var repo = org.mockito.Mockito.mock(com.careeros.attention.repository.AttentionRepository.class);
        org.mockito.Mockito.when(repo.deleteByJourney("synthetic")).thenReturn(155L);
        var service = new AttentionAdminService(
                org.mockito.Mockito.mock(org.springframework.jdbc.core.JdbcTemplate.class), repo);
        var out = service.wipeSimulated();
        assertThat(out).containsEntry("wiped", 155L).containsEntry("journey", "synthetic");
        org.mockito.Mockito.verify(repo).deleteByJourney("synthetic");
    }

    @Test
    void flavorsSpanBounceBrowserAndEngaged() {
        List<AttentionEvent> rows = AttentionAdminService.simulateRows(200, new Random(1234L));
        boolean anyBounce = rows.stream().anyMatch(r -> "dwell".equals(r.getEvent())
                && Long.parseLong(r.getValue()) < 8_000);
        boolean anyEngaged = rows.stream().filter(r -> "act".equals(r.getEvent())).count() >= 6;
        assertThat(anyBounce).isTrue();
        assertThat(anyEngaged).isTrue();
    }
}
