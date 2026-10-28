package com.careeros.report.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

import com.careeros.auth.service.EmailSender;
import com.careeros.report.entity.WeeklyDigest;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

/**
 * The letter's readable half (roadmap 21.2).
 *
 * <p>What is pinned: the mail is the stored payload laid out, not a second reading of the
 * board -- every line the payload carries appears, a key it does not carry drops its line
 * instead of printing a zero the engine never said, a long stalled list is capped rather than
 * mailed whole, and the transport receives exactly the rendered letter for the account.
 */
class WeeklyDigestMailerTest {

    private static final LocalDate WEEK = LocalDate.of(2026, 10, 26);

    @Test
    void theLetterIsThePayloadLaidOutForAMailbox() {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("windowDays", 7);
        payload.put("totalApplications", 12);
        payload.put("activePipeline", 7);
        Map<String, Object> mix = new LinkedHashMap<>();
        mix.put("saved", 3);
        mix.put("applied", 5);
        payload.put("stageCounts", mix);
        payload.put("responseRate", 0.42);
        payload.put("offerRate", 0.08);
        payload.put("stalledCount", 2);
        payload.put("stalled", List.of(
                Map.of("title", "Backend Engineer", "company", "Acme", "daysSinceLastActivity", 9),
                Map.of("title", "Data Analyst", "daysSinceLastActivity", 12)));
        payload.put("signals", List.of("2 application(s) have gone quiet past 7 days."));

        String letter = WeeklyDigestMailer.letterBody(WEEK, payload);

        assertThat(WeeklyDigestMailer.subject(WEEK))
                .isEqualTo("Your week in applications (26 Oct 2026)");
        assertThat(letter).contains(
                "Week of 26 October 2026.",
                "Applications on the board: 12 (7 active)",
                "Stage mix: saved 3, applied 5",
                "Response rate: 42% | Offer rate: 8%",
                "Stalled - no movement in 7+ days: 2",
                "  - Backend Engineer at Acme (9 days)",
                "  - Data Analyst (12 days)",
                "What the week says:",
                "  - 2 application(s) have gone quiet past 7 days.");
    }

    @Test
    void aKeyThePayloadDoesNotCarryDropsItsLineInsteadOfPrintingAZero() {
        String letter = WeeklyDigestMailer.letterBody(WEEK, Map.of("totalApplications", 4));

        assertThat(letter).contains("Applications on the board: 4");
        assertThat(letter).doesNotContain("active)");
        assertThat(letter).doesNotContain(
                "Stage mix", "Response rate", "Stalled", "What the week says");
    }

    @Test
    void aLongStalledListIsCappedAndTheRestCounted() {
        List<Map<String, Object>> stalled = new ArrayList<>();
        for (int i = 1; i <= 13; i++) {
            stalled.add(Map.of("title", "Role " + i, "daysSinceLastActivity", i));
        }
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("windowDays", 7);
        payload.put("stalledCount", 13);
        payload.put("stalled", stalled);

        String letter = WeeklyDigestMailer.letterBody(WEEK, payload);

        assertThat(letter).contains("  - Role 10 (10 days)", "  ... and 3 more");
        assertThat(letter).doesNotContain("Role 11");
        assertThat(letter).doesNotContain("Applications on the board");
    }

    @Test
    void theTransportReceivesTheRenderedLetterForTheAccount() {
        EmailSender email = mock(EmailSender.class);
        WeeklyDigest letter = new WeeklyDigest();
        letter.setWeekStart(WEEK);
        letter.setPayload(Map.of("totalApplications", 2));

        new WeeklyDigestMailer(email).send("alice@example.com", letter);

        verify(email).send("alice@example.com",
                "Your week in applications (26 Oct 2026)",
                "Week of 26 October 2026.\n\nApplications on the board: 2\n");
    }
}
