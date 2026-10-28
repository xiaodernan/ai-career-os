package com.careeros.report.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.common.PageDTO;
import com.careeros.report.dto.NightlyReportDtos.NightlyReportItem;
import com.careeros.report.dto.NightlyReportDtos.NightlyReportRequest;
import com.careeros.report.dto.NightlyReportDtos.NightlyReportStep;
import com.careeros.report.dto.NightlyReportDtos.NightlyVerdict;
import com.careeros.report.entity.NightlyReport;
import com.careeros.report.repository.NightlyReportRepository;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.test.util.ReflectionTestUtils;

/**
 * The nightly history's write rules (roadmap 20.1).
 *
 * <p>The only writer is the nightly job, so a malformed report is a caller bug and the
 * service must say so with a code of its own and the sentence that names the fault -- not
 * let a CHECK constraint answer as a 500 halfway through the night. Each refusal has one
 * meaning, so each gets its own code: a translated client can then say what went wrong
 * instead of "request validation failed". The read side is one page, newest first; the
 * clamping itself belongs to {@code Paging} and is asserted here only to prove the service
 * spends it. Every write also republishes the two gauges the alarm stack reads (roadmap
 * 20.3), and a boot republishes the stored history once, so a restart cannot silence a streak
 * the database still holds.
 */
class NightlyReportServiceTest {

    private static final OffsetDateTime START = OffsetDateTime.parse("2026-10-27T03:17:00Z");
    private static final OffsetDateTime END = OffsetDateTime.parse("2026-10-27T03:41:12Z");

    private NightlyReportRepository reports;
    private SimpleMeterRegistry registry;
    private NightlyReportService service;

    @BeforeEach
    void setUp() {
        reports = mock(NightlyReportRepository.class);
        registry = new SimpleMeterRegistry();
        service = new NightlyReportService(reports, new NightlyVerdictMetrics(registry));
        when(reports.save(any(NightlyReport.class))).thenAnswer(invocation -> {
            NightlyReport row = invocation.getArgument(0);
            ReflectionTestUtils.setField(row, "id", UUID.randomUUID());
            return row;
        });
    }

    private double lastFinished() {
        return registry.get(NightlyVerdictMetrics.LAST_FINISHED).gauge().value();
    }

    private double streak() {
        return registry.get(NightlyVerdictMetrics.CONSECUTIVE_FAILURES).gauge().value();
    }

    private static NightlyReportRequest request(String status, OffsetDateTime started,
                                                OffsetDateTime finished, String source,
                                                Map<String, Object> summary) {
        return new NightlyReportRequest(started, finished, status, source, "d8199f8",
                "https://github.example/actions/runs/1", summary);
    }

    @Test
    void a_night_is_recorded_with_the_reading_it_posted() {
        Map<String, Object> summary = Map.of("steps", List.of(Map.of("name", "backend-it", "status", "passed")));
        newestNights();

        NightlyReportItem item = service.record(request("PASSED ", START, END, " ", summary));

        assertThat(item.id()).isNotNull();
        assertThat(item.status()).isEqualTo("passed");
        assertThat(item.source()).isEqualTo("nightly");
        assertThat(item.commitSha()).isEqualTo("d8199f8");
        assertThat(item.runUrl()).isEqualTo("https://github.example/actions/runs/1");
        assertThat(item.startedAt()).isEqualTo(START);
        assertThat(item.finishedAt()).isEqualTo(END);
        assertThat(item.steps()).containsExactly(new NightlyReportStep("backend-it", "passed", null));
        assertThat(item.createdAt()).isNotNull();
        verify(reports).save(any(NightlyReport.class));
    }

    @Test
    void the_steps_are_lifted_out_of_the_summary_and_a_nameless_row_is_dropped() {
        Map<String, Object> summary = Map.of("steps", List.of(
                Map.of("status", "passed"),                                  // no name: says nothing
                Map.of("name", " eval ", "status", " passed ",
                        "detail", "recall_at_k 0.812 · 26 cases"),
                "not-a-row"));
        newestNights();

        NightlyReportItem item = service.record(request("passed", START, END, null, summary));

        assertThat(item.steps()).containsExactly(new NightlyReportStep("eval", "passed",
                "recall_at_k 0.812 · 26 cases"));
    }

    @Test
    void a_summary_without_steps_answers_an_empty_list_rather_than_null() {
        newestNights();

        NightlyReportItem item = service.record(request("passed", START, END, null, Map.of()));

        assertThat(item.steps()).isEmpty();
    }

    @Test
    void a_retried_post_is_answered_with_the_row_the_first_attempt_wrote() {
        NightlyReport stored = night(NightlyReport.STATUS_FAILED, END);
        when(reports.findBySourceAndStartedAtAndFinishedAt("nightly", START, END))
                .thenReturn(Optional.of(stored));
        newestNights(stored);

        NightlyReportItem item = service.record(request("failed", START, END, null, Map.of()));

        assertThat(item.id())
                .as("the retry answers the stored row, so one failed night cannot become two")
                .isEqualTo(stored.getId());
        verify(reports, never()).save(any(NightlyReport.class));
    }

    @Test
    void a_span_that_ends_later_is_another_night_even_from_the_same_start() {
        OffsetDateTime laterEnd = END.plusMinutes(3);
        when(reports.findBySourceAndStartedAtAndFinishedAt("nightly", START, laterEnd))
                .thenReturn(Optional.empty());
        newestNights(night(NightlyReport.STATUS_PASSED, laterEnd));

        NightlyReportItem item = service.record(request("passed", START, laterEnd, null, Map.of()));

        verify(reports).findBySourceAndStartedAtAndFinishedAt("nightly", START, laterEnd);
        verify(reports).save(any(NightlyReport.class));
        assertThat(item.finishedAt()).isEqualTo(laterEnd);
        assertThat(lastFinished()).isEqualTo((double) laterEnd.toEpochSecond());
    }

    @Test
    void a_status_outside_passed_or_failed_is_refused_with_its_own_code() {
        assertThatThrownBy(() -> service.record(request("green", START, END, null, Map.of())))
                .isInstanceOfSatisfying(ApiException.class, ex -> {
                    assertThat(ex.code()).isEqualTo(ApiErrorCode.NIGHTLY_REPORT_STATUS_INVALID);
                    assertThat(ex.getMessage()).contains("passed or failed").contains("green");
                    assertThat(ex.details()).isEmpty();
                });
    }

    @Test
    void a_night_cannot_finish_before_it_started() {
        assertThatThrownBy(() -> service.record(request("passed", END, START, null, Map.of())))
                .isInstanceOfSatisfying(ApiException.class, ex -> {
                    assertThat(ex.code()).isEqualTo(ApiErrorCode.NIGHTLY_REPORT_CLOCK_REVERSED);
                    assertThat(ex.getMessage()).isEqualTo("A nightly report cannot finish before it started");
                });
    }

    @Test
    void a_summary_with_more_top_level_entries_than_the_column_allows_is_refused() {
        Map<String, Object> oversized = new HashMap<>();
        for (int i = 0; i <= 40; i++) {
            oversized.put("step-" + i, "passed");
        }

        assertThatThrownBy(() -> service.record(request("passed", START, END, null, oversized)))
                .isInstanceOfSatisfying(ApiException.class,
                        ex -> assertThat(ex.code()).isEqualTo(ApiErrorCode.NIGHTLY_REPORT_SUMMARY_TOO_LARGE));
    }

    @Test
    void the_list_is_newest_first_in_a_window_paging_has_already_made_safe() {
        NightlyReport row = new NightlyReport();
        ReflectionTestUtils.setField(row, "id", UUID.randomUUID());
        row.setSource("nightly");
        row.setStatus(NightlyReport.STATUS_FAILED);
        row.setStartedAt(START);
        row.setFinishedAt(END);
        row.setSummary(Map.of());
        row.setCreatedAt(END);
        Pageable window = PageRequest.of(0, 100);
        when(reports.findAllByOrderByStartedAtDescIdDesc(window))
                .thenReturn(new PageImpl<>(List.of(row), window, 1));

        PageDTO<NightlyReportItem> page = service.list(-3, 500);

        assertThat(page.items()).hasSize(1);
        assertThat(page.items().get(0).status()).isEqualTo("failed");
        assertThat(page.total()).isEqualTo(1);
        assertThat(page.page()).isZero();
        assertThat(page.size()).isEqualTo(100);
    }

    private static NightlyReport night(String status, OffsetDateTime finishedAt) {
        NightlyReport row = new NightlyReport();
        ReflectionTestUtils.setField(row, "id", UUID.randomUUID());
        row.setSource("nightly");
        row.setStatus(status);
        row.setCommitSha("d8199f8");
        row.setRunUrl("https://github.example/actions/runs/1");
        row.setStartedAt(finishedAt.minusMinutes(24));
        row.setFinishedAt(finishedAt);
        row.setSummary(Map.of());
        row.setCreatedAt(finishedAt);
        return row;
    }

    private void newestNights(NightlyReport... rows) {
        Pageable window = PageRequest.of(0, NightlyReportService.STREAK_WINDOW);
        when(reports.findAllByOrderByStartedAtDescIdDesc(window))
                .thenReturn(new PageImpl<>(List.of(rows), window, rows.length));
    }

    @Test
    void an_install_with_no_nights_is_missing_rather_than_green() {
        newestNights();

        NightlyVerdict verdict = service.verdict();

        assertThat(verdict.status()).isEqualTo(NightlyVerdict.MISSING);
        assertThat(verdict.finishedAt()).isNull();
        assertThat(verdict.consecutiveFailures()).isZero();
        assertThat(verdict.stale()).isTrue();
        assertThat(verdict.staleAfterHours()).isEqualTo(NightlyReportService.STALE_AFTER_HOURS);
    }

    @Test
    void the_verdict_is_the_newest_nights_own_word() {
        newestNights(night(NightlyReport.STATUS_PASSED, OffsetDateTime.now().minusHours(2)));

        NightlyVerdict verdict = service.verdict();

        assertThat(verdict.status()).isEqualTo("passed");
        assertThat(verdict.consecutiveFailures()).isZero();
        assertThat(verdict.stale()).isFalse();
        assertThat(verdict.commitSha()).isEqualTo("d8199f8");
        assertThat(verdict.runUrl()).isEqualTo("https://github.example/actions/runs/1");
    }

    @Test
    void a_failure_streak_counts_the_nights_before_the_failures_stopped() {
        OffsetDateTime now = OffsetDateTime.now();
        newestNights(
                night(NightlyReport.STATUS_FAILED, now.minusHours(2)),
                night(NightlyReport.STATUS_FAILED, now.minusHours(26)),
                night(NightlyReport.STATUS_PASSED, now.minusHours(50)),
                night(NightlyReport.STATUS_FAILED, now.minusHours(74)));

        NightlyVerdict verdict = service.verdict();

        assertThat(verdict.status()).isEqualTo("failed");
        assertThat(verdict.consecutiveFailures()).isEqualTo(2);
        assertThat(verdict.stale()).isFalse();
    }

    @Test
    void a_passed_night_ends_the_streak_instead_of_being_hidden_by_it() {
        OffsetDateTime now = OffsetDateTime.now();
        newestNights(
                night(NightlyReport.STATUS_PASSED, now.minusHours(2)),
                night(NightlyReport.STATUS_FAILED, now.minusHours(26)),
                night(NightlyReport.STATUS_FAILED, now.minusHours(50)));

        NightlyVerdict verdict = service.verdict();

        assertThat(verdict.status()).isEqualTo("passed");
        assertThat(verdict.consecutiveFailures()).isZero();
        assertThat(verdict.stale()).isFalse();
    }

    @Test
    void a_record_that_stopped_arriving_is_stale_even_when_it_passed() {
        newestNights(night(NightlyReport.STATUS_PASSED,
                OffsetDateTime.now().minusHours(NightlyReportService.STALE_AFTER_HOURS + 1L)));

        NightlyVerdict verdict = service.verdict();

        assertThat(verdict.status()).isEqualTo("passed");
        assertThat(verdict.stale()).isTrue();
        assertThat(verdict.staleAfterHours()).isEqualTo(NightlyReportService.STALE_AFTER_HOURS);
    }

    @Test
    void a_recorded_night_republishes_the_verdict_as_gauges() {
        newestNights(
                night(NightlyReport.STATUS_FAILED, END),
                night(NightlyReport.STATUS_FAILED, END.minusHours(24)));

        service.record(request("failed", START, END, null, Map.of()));

        assertThat(lastFinished()).isEqualTo((double) END.toEpochSecond());
        assertThat(streak())
                .as("the alarm and the page read the same streak, and this one ends at the first pass")
                .isEqualTo(2.0);
    }

    @Test
    void a_boot_republishes_the_stored_history_instead_of_starting_from_zero() {
        OffsetDateTime now = OffsetDateTime.now();
        newestNights(
                night(NightlyReport.STATUS_FAILED, now.minusHours(2)),
                night(NightlyReport.STATUS_PASSED, now.minusHours(26)),
                night(NightlyReport.STATUS_FAILED, now.minusHours(50)));

        service.publishStartupVerdict();

        assertThat(lastFinished()).isEqualTo((double) now.minusHours(2).toEpochSecond());
        assertThat(streak()).isEqualTo(1.0);
    }

    @Test
    void a_boot_whose_read_fails_keeps_the_boot_defaults_rather_than_refusing_to_start() {
        when(reports.findAllByOrderByStartedAtDescIdDesc(any(Pageable.class)))
                .thenThrow(new IllegalStateException("the database is not up yet"));

        assertThatCode(service::publishStartupVerdict).doesNotThrowAnyException();
        assertThat(lastFinished())
                .as("boot time: the documented grace, not a fabricated finish")
                .isCloseTo(Instant.now().getEpochSecond(), within(10.0));
        assertThat(streak()).isZero();
    }
}
