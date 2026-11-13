package com.careeros.report.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.careeros.report.dto.ActivityHeatmapDtos.ActivityHeatmapResponse;
import com.careeros.report.dto.ActivityHeatmapDtos.HeatmapDay;
import com.careeros.report.repository.ActivityHeatmapRepository;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;

/**
 * The heatmap service's own arithmetic: the dense fill (a grid that skips quiet days
 * lies by omission), the streak pair (current forgives today, longest walks the whole
 * window), and the window clamp. The SQL is the repository's; what this class owns is
 * the shape the browser's grid consumes without a second pass.
 */
class ActivityHeatmapServiceTest {

    private final UUID userId = UUID.randomUUID();
    private final ActivityHeatmapRepository repository = mock(ActivityHeatmapRepository.class);
    private final ActivityHeatmapService service = new ActivityHeatmapService(repository);

    private LocalDate today() {
        return LocalDate.now(ZoneOffset.UTC);
    }

    @Test
    void theWindowIsDense_zeroDaysAreInTheGridNotSkipped() {
        when(repository.dailyCounts(eq(userId), any())).thenReturn(List.of(
                new ActivityHeatmapRepository.DayCount(today(), "application", 2L)));

        ActivityHeatmapResponse response = service.build(userId, 14);

        assertThat(response.days()).isEqualTo(14);
        assertThat(response.grid()).hasSize(14);
        assertThat(response.grid().get(13).date()).isEqualTo(today().toString());
        assertThat(response.grid().get(13).applications()).isEqualTo(2);
        // Everything before today is the silence the grid must not omit.
        assertThat(response.grid().get(0).total()).isZero();
        assertThat(response.grandTotal()).isEqualTo(2);
    }

    @Test
    void theCurrentStreakForgivesAnInactiveToday() {
        // A chain that ends yesterday (today, the day the reader is in, still empty):
        // the streak must read 3, not 0, or every morning reads "you broke it".
        LocalDate today = today();
        List<HeatmapDay> grid = List.of(
                day(today.minusDays(3), 1),
                day(today.minusDays(2), 1),
                day(today.minusDays(1), 1),
                day(today, 0));

        assertThat(ActivityHeatmapService.currentStreak(grid)).isEqualTo(3);
    }

    @Test
    void anInactiveYesterdayBreaksTheStreakEvenWithAForgivenToday() {
        LocalDate today = today();
        List<HeatmapDay> grid = List.of(
                day(today.minusDays(3), 1),
                day(today.minusDays(2), 0),
                day(today.minusDays(1), 1),
                day(today, 0));

        assertThat(ActivityHeatmapService.currentStreak(grid)).isEqualTo(1);
    }

    @Test
    void theLongestStreakSurvivesQuietDaysBetweenRuns() {
        LocalDate today = today();
        List<HeatmapDay> grid = List.of(
                day(today.minusDays(4), 1),
                day(today.minusDays(3), 1),
                day(today.minusDays(2), 1),
                day(today.minusDays(1), 0),
                day(today, 1));

        assertThat(ActivityHeatmapService.longestStreak(grid)).isEqualTo(3);
    }

    @Test
    void theWindowClampsToTheDocumentedBounds() {
        when(repository.dailyCounts(eq(userId), any())).thenReturn(List.of());

        assertThat(service.build(userId, 1).days()).isEqualTo(ActivityHeatmapService.MIN_DAYS);
        assertThat(service.build(userId, 9999).days()).isEqualTo(ActivityHeatmapService.MAX_DAYS);
    }

    private HeatmapDay day(LocalDate date, int total) {
        return new HeatmapDay(date.toString(), total, 0, 0, 0);
    }
}
