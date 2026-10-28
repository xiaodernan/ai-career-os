package com.careeros.report.web;

import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUserArgumentResolver;
import com.careeros.common.EnvelopeAdvice;
import com.careeros.common.GlobalExceptionHandler;
import com.careeros.report.dto.WeeklyDigestDtos.WeeklyDigestDto;
import com.careeros.report.service.WeeklyDigestService;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.converter.json.Jackson2ObjectMapperBuilder;
import org.springframework.http.converter.json.MappingJackson2HttpMessageConverter;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

/**
 * The weekly letter's two routes (roadmap 19.4).
 *
 * <p>The list is scoped to the caller and the compose route takes no input at all: the week is
 * "now", and the window is the letter's own. What this pins is that both travel with the
 * principal rather than anything in the request, and that the letter's week is a date, not a
 * moment -- a timestamp would invite a reader to convert it and land on the Sunday before.
 */
class WeeklyDigestControllerTest {

    private static final String USER = "6b0178a0-d352-09c3-ea65-8f107bd28d01";

    private WeeklyDigestService digests;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        digests = mock(WeeklyDigestService.class);
        // the app's own mapper disables WRITE_DATES_AS_TIMESTAMPS (EnvelopeJson); MockMvc's default
        // writes a LocalDate as [2026,10,26], which is not what the browser receives
        MappingJackson2HttpMessageConverter dates = new MappingJackson2HttpMessageConverter(
                Jackson2ObjectMapperBuilder.json()
                        .featuresToDisable(
                                com.fasterxml.jackson.databind.SerializationFeature.WRITE_DATES_AS_TIMESTAMPS)
                        .build());
        mvc = MockMvcBuilders.standaloneSetup(new WeeklyDigestController(digests))
                .setControllerAdvice(new EnvelopeAdvice(), new GlobalExceptionHandler())
                .setCustomArgumentResolvers(new CurrentUserArgumentResolver())
                .setMessageConverters(dates)
                .build();
        SecurityContextHolder.getContext().setAuthentication(new UsernamePasswordAuthenticationToken(
                new AuthUser(UUID.fromString(USER), "ada@example.invalid", "user"), null, List.of()));
    }

    @AfterEach
    void tearDown() {
        SecurityContextHolder.clearContext();
    }

    private static WeeklyDigestDto letter(Map<String, Object> payload) {
        return new WeeklyDigestDto(UUID.fromString("44444444-4444-4444-8444-444444444444"),
                LocalDate.of(2026, 10, 26), 7, OffsetDateTime.parse("2026-10-27T08:00:00Z"), payload,
                null, null, 0);
    }

    @Test
    void theListIsTheCallersOwnLetters() throws Exception {
        when(digests.recent(UUID.fromString(USER)))
                .thenReturn(List.of(letter(Map.of("totalApplications", 4))));

        mvc.perform(get("/api/v1/digests"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data[0].weekStart").value("2026-10-26"))
                .andExpect(jsonPath("$.data[0].windowDays").value(7))
                .andExpect(jsonPath("$.data[0].payload.totalApplications").value(4))
                .andExpect(jsonPath("$.data[0].deliveryAttempts").value(0));

        verify(digests).recent(UUID.fromString(USER));
    }

    /**
     * The receipt is the letter's own (21.3): when it last left, the transport's last refusal
     * and how many attempts it has had. The page prints its sentence from these three; a
     * delivered letter that reads as unsent (or the reverse) is the defect this pins.
     */
    @Test
    void theLetterCarriesItsDeliveryReceipt() throws Exception {
        WeeklyDigestDto refused = new WeeklyDigestDto(
                UUID.fromString("44444444-4444-4444-8444-444444444444"),
                LocalDate.of(2026, 10, 26), 7, OffsetDateTime.parse("2026-10-27T08:00:00Z"),
                Map.of("stalledCount", 1), OffsetDateTime.parse("2026-10-27T09:05:00Z"),
                "relay said 550", 3);
        when(digests.recent(UUID.fromString(USER))).thenReturn(List.of(refused));

        mvc.perform(get("/api/v1/digests"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data[0].deliveredAt").value("2026-10-27T09:05:00Z"))
                .andExpect(jsonPath("$.data[0].deliveryError").value("relay said 550"))
                .andExpect(jsonPath("$.data[0].deliveryAttempts").value(3));
    }

    @Test
    void composingNowAnswersTheFiledLetterForTheCaller() throws Exception {
        when(digests.composeNow(UUID.fromString(USER)))
                .thenReturn(letter(Map.of("stalledCount", 1)));

        mvc.perform(post("/api/v1/digests/run"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.id").value("44444444-4444-4444-8444-444444444444"))
                .andExpect(jsonPath("$.data.payload.stalledCount").value(1));

        verify(digests).composeNow(UUID.fromString(USER));
    }
}
