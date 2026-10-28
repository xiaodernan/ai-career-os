package com.careeros.report.web;

import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUserArgumentResolver;
import com.careeros.common.EnvelopeAdvice;
import com.careeros.common.GlobalExceptionHandler;
import com.careeros.common.PageDTO;
import com.careeros.report.dto.NightlyReportDtos.NightlyReportItem;
import com.careeros.report.dto.NightlyReportDtos.NightlyReportRequest;
import com.careeros.report.dto.NightlyReportDtos.NightlyReportStep;
import com.careeros.report.service.MonitoringService;
import com.careeros.report.service.NightlyReportService;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

/**
 * The monitoring routes' second half (roadmap 20.1): the nightly history, and the internal
 * door the night writes it through.
 *
 * <p>Two promises are worth a route test. The read is deployment-wide, so it must not be
 * quietly scoped to whoever happens to be signed in; and the write is a caller bug's last
 * checkpoint -- a body the recorder cannot have meant (no status, an impossible span) comes
 * back as a 400 with a sentence, not a 500 from a database constraint.
 */
class MonitoringControllerTest {

    private static final UUID ALICE = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final UUID REPORT = UUID.fromString("55555555-5555-4555-8555-555555555555");

    private MonitoringService monitoring;
    private NightlyReportService reports;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        monitoring = mock(MonitoringService.class);
        reports = mock(NightlyReportService.class);
        mvc = MockMvcBuilders.standaloneSetup(
                        new MonitoringController(monitoring, reports),
                        new InternalNightlyReportController(reports))
                .setControllerAdvice(new EnvelopeAdvice(), new GlobalExceptionHandler())
                .setCustomArgumentResolvers(new CurrentUserArgumentResolver())
                .build();
        SecurityContextHolder.getContext().setAuthentication(new UsernamePasswordAuthenticationToken(
                new AuthUser(ALICE, "ada@example.invalid", "user"), null, List.of()));
    }

    @AfterEach
    void tearDown() {
        SecurityContextHolder.clearContext();
    }

    private static NightlyReportItem item(String status) {
        return new NightlyReportItem(REPORT, "nightly", status, "d8199f8",
                "https://github.example/actions/runs/1",
                OffsetDateTime.parse("2026-10-27T03:17:00Z"),
                OffsetDateTime.parse("2026-10-27T03:41:12Z"),
                List.of(new NightlyReportStep("backend-it", "passed", null)),
                OffsetDateTime.parse("2026-10-27T03:41:13Z"));
    }

    @Test
    void the_health_report_is_the_callers_own() throws Exception {
        when(monitoring.healthReport(ALICE)).thenReturn(Map.of("verdict", "healthy"));

        mvc.perform(get("/api/v1/monitoring/health-report"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.verdict").value("healthy"));

        verify(monitoring).healthReport(ALICE);
    }

    @Test
    void the_nightly_history_is_read_newest_first_with_the_routes_defaults() throws Exception {
        when(reports.list(0, 10)).thenReturn(
                new PageDTO<>(List.of(item("passed")), 1, 0, 10));

        mvc.perform(get("/api/v1/monitoring/nightly-reports"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.items[0].status").value("passed"))
                .andExpect(jsonPath("$.data.items[0].commitSha").value("d8199f8"))
                .andExpect(jsonPath("$.data.items[0].steps[0].name").value("backend-it"))
                .andExpect(jsonPath("$.data.items[0].steps[0].status").value("passed"))
                .andExpect(jsonPath("$.data.total").value(1))
                .andExpect(jsonPath("$.data.page").value(0))
                .andExpect(jsonPath("$.data.size").value(10));

        verify(reports).list(0, 10);
    }

    @Test
    void a_reader_asking_for_another_page_gets_the_page_they_asked_for() throws Exception {
        when(reports.list(2, 5)).thenReturn(new PageDTO<>(List.of(), 11, 2, 5));

        mvc.perform(get("/api/v1/monitoring/nightly-reports?page=2&size=5"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.total").value(11))
                .andExpect(jsonPath("$.data.page").value(2));

        verify(reports).list(2, 5);
    }

    @Test
    void the_night_writes_its_record_through_the_internal_door() throws Exception {
        when(reports.record(org.mockito.ArgumentMatchers.any(NightlyReportRequest.class)))
                .thenReturn(item("failed"));

        mvc.perform(post("/api/internal/nightly-reports")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"startedAt":"2026-10-27T03:17:00Z",
                                 "finishedAt":"2026-10-27T03:41:12Z",
                                 "status":"failed",
                                 "source":"nightly",
                                 "commitSha":"d8199f8",
                                 "runUrl":"https://github.example/actions/runs/1",
                                 "summary":{"steps":[{"name":"backend-it","status":"failed"}]}}
                                """))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.data.status").value("failed"));

        verify(reports).record(new NightlyReportRequest(
                OffsetDateTime.parse("2026-10-27T03:17:00Z"),
                OffsetDateTime.parse("2026-10-27T03:41:12Z"),
                "failed", "nightly", "d8199f8",
                "https://github.example/actions/runs/1",
                Map.of("steps", List.of(Map.of("name", "backend-it", "status", "failed")))));
    }

    @Test
    void a_report_with_no_status_is_refused_before_the_service_sees_it() throws Exception {
        mvc.perform(post("/api/internal/nightly-reports")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"startedAt":"2026-10-27T03:17:00Z",
                                 "finishedAt":"2026-10-27T03:41:12Z",
                                 "summary":{}}
                                """))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("VALIDATION_FAILED"));

        verify(reports, org.mockito.Mockito.never())
                .record(org.mockito.ArgumentMatchers.any(NightlyReportRequest.class));
    }

    @Test
    void a_bodys_refusal_from_the_service_keeps_its_code_and_sentence() throws Exception {
        when(reports.record(org.mockito.ArgumentMatchers.any(NightlyReportRequest.class)))
                .thenThrow(new ApiException(ApiErrorCode.NIGHTLY_REPORT_CLOCK_REVERSED,
                        "A nightly report cannot finish before it started"));

        mvc.perform(post("/api/internal/nightly-reports")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"startedAt":"2026-10-27T03:41:12Z",
                                 "finishedAt":"2026-10-27T03:17:00Z",
                                 "status":"passed","summary":{}}
                                """))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("NIGHTLY_REPORT_CLOCK_REVERSED"))
                .andExpect(jsonPath("$.error.message")
                        .value("A nightly report cannot finish before it started"));
    }
}
