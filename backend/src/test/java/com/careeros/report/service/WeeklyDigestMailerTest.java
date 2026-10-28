package com.careeros.report.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

import com.careeros.auth.service.EmailSender;
import com.careeros.mail.service.MailLinks;
import com.careeros.mail.service.MailList;
import com.careeros.report.entity.WeeklyDigest;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

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
    private static final UUID READER = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final String SETTINGS = "https://careeros.example/settings/1/signature";
    private static final MailLinks LINKS = new MailLinks("test-secret", "https://careeros.example");

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

        String letter = WeeklyDigestMailer.letterBody(WEEK, payload, "en", SETTINGS);

        assertThat(WeeklyDigestMailer.subject(WEEK, "en"))
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
        String letter = WeeklyDigestMailer.letterBody(WEEK, Map.of("totalApplications", 4), "en", SETTINGS);

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

        String letter = WeeklyDigestMailer.letterBody(WEEK, payload, "en", SETTINGS);

        assertThat(letter).contains("  - Role 10 (10 days)", "  ... and 3 more");
        assertThat(letter).doesNotContain("Role 11");
        assertThat(letter).doesNotContain("Applications on the board");
    }

    @Test
    void theTransportReceivesTheRenderedLetterForTheAccount() {
        EmailSender email = mock(EmailSender.class);
        WeeklyDigest letter = new WeeklyDigest();
        letter.setUserId(READER);
        letter.setWeekStart(WEEK);
        letter.setPayload(Map.of("totalApplications", 2));

        new WeeklyDigestMailer(email, LINKS).send("alice@example.com", letter);

        verify(email).send("alice@example.com",
                "Your week in applications (26 Oct 2026)",
                "Week of 26 October 2026.\n\nApplications on the board: 2\n"
                        + "Stop these letters: " + LINKS.page(READER) + "\n",
                LINKS.oneClick(READER, MailList.WEEKLY));
    }

    /**
     * The Monday letter's way out names its own list (roadmap 23.1): a one-click from this
     * letter must not also silence the morning signals, so the header carries the POST for
     * the weekly list and nothing else.
     */
    @Test
    void theMondayLetterCarriesTheOneClickForTheWeeklyListOnly() {
        EmailSender email = mock(EmailSender.class);
        WeeklyDigest letter = new WeeklyDigest();
        letter.setUserId(READER);
        letter.setWeekStart(WEEK);
        letter.setPayload(Map.of("totalApplications", 2));

        new WeeklyDigestMailer(email, LINKS).send("alice@example.com", letter);

        @SuppressWarnings("unchecked")
        ArgumentCaptor<Map<String, String>> headers = ArgumentCaptor.forClass(Map.class);
        verify(email).send(eq("alice@example.com"), anyString(), anyString(), headers.capture());
        assertThat(headers.getValue()).containsEntry("List-Unsubscribe",
                "<https://careeros.example/api/v1/mail/preferences/" + READER + "/"
                        + LINKS.token(READER) + "/stop/weekly>");
    }

    @Test
    void aChineseLetterIsTheSameReadingsInChineseWords() {
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

        String letter = WeeklyDigestMailer.letterBody(WEEK, payload, "zh", SETTINGS);

        assertThat(WeeklyDigestMailer.subject(WEEK, "zh"))
                .isEqualTo("你的求职周报（2026年10月26日）");
        assertThat(letter).contains(
                "2026年10月26日 这一周。",
                "板上投递：12（进行中 7）",
                "阶段分布：已收藏 3、已投递 5",
                "回复率 42% | 录取率 8%",
                "停滞 —— 7 天以上没有动静：2",
                "  - Acme 的 Backend Engineer（9 天）",
                "  - Data Analyst（12 天）",
                "这一周告诉我们：",
                "  - 2 application(s) have gone quiet past 7 days.");
    }

    @Test
    void theTransportReceivesTheLettersOwnLanguage() {
        EmailSender email = mock(EmailSender.class);
        WeeklyDigest letter = new WeeklyDigest();
        letter.setUserId(READER);
        letter.setWeekStart(WEEK);
        letter.setLocale("zh");
        letter.setPayload(Map.of("totalApplications", 2));

        new WeeklyDigestMailer(email, LINKS).send("alice@example.com", letter);

        verify(email).send("alice@example.com", "你的求职周报（2026年10月26日）",
                "2026年10月26日 这一周。\n\n板上投递：2\n"
                        + "不想再收到这些信：" + LINKS.page(READER) + "\n",
                LINKS.oneClick(READER, MailList.WEEKLY));
    }
}
