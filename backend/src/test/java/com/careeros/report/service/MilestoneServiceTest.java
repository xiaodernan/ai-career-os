package com.careeros.report.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.careeros.application.repository.ApplicationLetterRepository;
import com.careeros.application.repository.ApplicationRepository;
import com.careeros.interview.repository.InterviewSessionRepository;
import com.careeros.job.repository.JobMatchRepository;
import com.careeros.offer.repository.OfferShelfRepository;
import com.careeros.offer.entity.OfferRow;
import com.careeros.report.dto.MilestoneDtos.MilestonesResponse;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

/**
 * The milestone shelf's arithmetic: thresholds read the counters they say they read,
 * a reached milestone carries no progress, a working one carries progress/target, and
 * the counters themselves are real numbers the page can quote (Epic 273). The
 * heatmap's streak is stubbed through its service's 28-day grid — the streak_week
 * badge reads the same chain the pace card draws.
 */
class MilestoneServiceTest {

    private final UUID userId = UUID.randomUUID();
    private ApplicationRepository applications;
    private InterviewSessionRepository interviews;
    private JobMatchRepository matches;
    private ApplicationLetterRepository letters;
    private OfferShelfRepository shelf;
    private MilestoneService service;

    @BeforeEach
    void setUp() {
        applications = mock(ApplicationRepository.class);
        interviews = mock(InterviewSessionRepository.class);
        matches = mock(JobMatchRepository.class);
        letters = mock(ApplicationLetterRepository.class);
        shelf = mock(OfferShelfRepository.class);
        var heatmap = mock(ActivityHeatmapService.class);
        when(heatmap.build(org.mockito.ArgumentMatchers.eq(userId),
                org.mockito.ArgumentMatchers.anyInt())).thenReturn(
            new com.careeros.report.dto.ActivityHeatmapDtos.ActivityHeatmapResponse(
                28, java.util.List.of(),
                new com.careeros.report.dto.ActivityHeatmapDtos.HeatmapStreak(3, 9), 30));
        service = new MilestoneService(applications, interviews, matches, letters, shelf, heatmap);
    }

    private void counters(long apps, long rehearsals, long offers, long lettersKept,
                          long matchesCount, int shelfRows) {
        when(applications.countByUserId(userId)).thenReturn(apps);
        when(applications.countByUserIdAndStatus(userId, "offer")).thenReturn(offers);
        when(interviews.countByUserIdAndStatus(userId, "completed")).thenReturn(rehearsals);
        when(letters.countByUserId(userId)).thenReturn(lettersKept);
        when(matches.countByUserId(userId)).thenReturn(matchesCount);
        var rows = java.util.stream.IntStream.range(0, shelfRows)
                .mapToObj(i -> new OfferRow()).toList();
        when(shelf.shelfOrder(userId)).thenReturn(rows);
    }

    @Test
    void anEmptyReaderHasOneBadgeWorkingAndNoneEarned() {
        counters(0, 0, 0, 0, 0, 0);
        MilestonesResponse out = service.build(userId);

        assertThat(out.counters().applications()).isZero();
        assertThat(out.milestones()).extracting(m -> m.key() + ":" + m.done())
                .contains("first_step:false", "streak_week:false");
        assertThat(out.milestones()).filteredOn(m -> m.done()).isEmpty();
        var first = out.milestones().stream()
                .filter(m -> m.key().equals("first_step")).findFirst().orElseThrow();
        assertThat(first.progress()).isZero();
        assertThat(first.target()).isEqualTo(1);
    }

    @Test
    void aReachedMilestoneCarriesNoProgress_andTheNextCarriesBoth() {
        counters(10, 0, 0, 0, 0, 0);
        MilestonesResponse out = service.build(userId);

        var ten = out.milestones().stream()
                .filter(m -> m.key().equals("ten_steps")).findFirst().orElseThrow();
        assertThat(ten.done()).isTrue();
        assertThat(ten.progress()).isNull();
        var fifty = out.milestones().stream()
                .filter(m -> m.key().equals("fifty_steps")).findFirst().orElseThrow();
        assertThat(fifty.done()).isFalse();
        assertThat(fifty.progress()).isEqualTo(10);
        assertThat(fifty.target()).isEqualTo(50);
    }

    @Test
    void theStreakBadgeReadsTheSameChainThePaceCardDraws() {
        counters(1, 0, 0, 0, 0, 0);
        MilestonesResponse out = service.build(userId);

        var streak = out.milestones().stream()
                .filter(m -> m.key().equals("streak_week")).findFirst().orElseThrow();
        assertThat(streak.done()).isFalse();
        assertThat(streak.progress()).isEqualTo(3);
        assertThat(streak.target()).isEqualTo(7);
        assertThat(out.counters().currentStreak()).isEqualTo(3);
    }

    @Test
    void theOfferBadgesReadBothHalvesTheBoardAndTheShelf() {
        counters(2, 0, 1, 0, 0, 2);
        MilestonesResponse out = service.build(userId);

        var firstOffer = out.milestones().stream()
                .filter(m -> m.key().equals("first_offer")).findFirst().orElseThrow();
        assertThat(firstOffer.done()).isTrue();
        var shelfFull = out.milestones().stream()
                .filter(m -> m.key().equals("shelf_full")).findFirst().orElseThrow();
        assertThat(shelfFull.done()).isFalse();
        assertThat(shelfFull.progress()).isEqualTo(2);
        assertThat(shelfFull.target()).isEqualTo(3);
    }
}
