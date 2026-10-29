package com.careeros.calendar.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.careeros.application.entity.Application;
import com.careeros.application.repository.ApplicationRepository;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;

/**
 * What the calendar feed says (roadmap 34.1).
 *
 * <p>A calendar is read by software, so the claims are structural: one event per reminder, a
 * UTC start the parser can compare, a stable UID so a poll updates the event instead of adding
 * a copy, an end half an hour later, and both a description and a URL that lead back to the
 * board. Past reminders stay: the document mirrors the board, so an event leaves when the
 * reader clears the reminder, not when the date slips by.
 *
 * <p>The text rules are the ones a calendar client will refuse the whole document over:
 * commas, semicolons, backslashes and newlines are escaped, and long lines fold at 75 octets
 * without splitting a multi-byte character. A Chinese title is where that last rule earns its
 * keep -- folding on characters would cut a glyph in half and every parser would drop the line.
 */
class CalendarFeedTest {

    private static final UUID ALICE = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final UUID APPLICATION = UUID.fromString("55555555-5555-4555-8555-555555555555");

    private static final OffsetDateTime UPDATED = OffsetDateTime.parse("2026-10-01T08:00:00Z");
    private static final OffsetDateTime CREATED = OffsetDateTime.parse("2026-09-30T07:00:00Z");

    private final ApplicationRepository applications = mock(ApplicationRepository.class);
    private final CalendarLinks links = new CalendarLinks("test-secret", "https://careeros.example");
    private final CalendarService service = new CalendarService(applications, links);

    private static Application row(OffsetDateTime reminder, String company, String title) {
        Application row = mock(Application.class);
        when(row.getId()).thenReturn(APPLICATION);
        when(row.getReminderAt()).thenReturn(reminder);
        when(row.getUpdatedAt()).thenReturn(UPDATED);
        when(row.getCreatedAt()).thenReturn(CREATED);
        when(row.getCompanyName()).thenReturn(company);
        when(row.getTitle()).thenReturn(title);
        return row;
    }

    private String render(List<Application> rows, String locale) {
        when(applications.findByUserIdAndReminderAtIsNotNullOrderByReminderAtAscIdAsc(ALICE))
                .thenReturn(rows);
        return service.feed(ALICE, locale);
    }

    private static OffsetDateTime at(String instant) {
        return OffsetDateTime.parse(instant);
    }

    /** RFC 5545 unfolds a line by removing CRLF + the one leading space. */
    private static String unfold(String ics) {
        return ics.replace("\r\n ", "");
    }

    @Test
    void aReminderBecomesOneEventWithItsTimeItsNameAndItsWayBack() {
        String ics = render(List.of(row(at("2026-10-30T10:00:00Z"), "Acme", "Backend Engineer")), "en");

        assertThat(ics).startsWith("BEGIN:VCALENDAR\r\n");
        assertThat(ics).endsWith("END:VCALENDAR\r\n");
        assertThat(ics).contains("BEGIN:VEVENT\r\n");
        assertThat(ics).contains("UID:" + APPLICATION + "@careeros\r\n");
        assertThat(ics).contains("DTSTART:20261030T100000Z\r\n");
        assertThat(ics).contains("DTEND:20261030T103000Z\r\n");
        assertThat(ics).contains("SUMMARY:Acme \u00b7 Backend Engineer\r\n");
        assertThat(ics).contains("DESCRIPTION:https://careeros.example/applications\r\n");
        assertThat(ics).contains("URL:https://careeros.example/applications\r\n");
        assertThat(ics).contains("STATUS:CONFIRMED\r\n");
        assertThat(ics).contains("TRANSP:TRANSPARENT\r\n");
    }

    @Test
    void theEventCarriesItsOwnAlarmAtTheReminderMoment() {
        String ics = render(List.of(row(at("2026-10-30T10:00:00Z"), "Acme", "Backend Engineer")), "en");

        assertThat(ics).contains("BEGIN:VALARM\r\n"
                + "ACTION:DISPLAY\r\n"
                + "DESCRIPTION:Acme \u00b7 Backend Engineer\r\n"
                + "TRIGGER:PT0M\r\n"
                + "END:VALARM\r\n");
    }

    @Test
    void aReminderThatPassedStaysOnTheFeedBecauseTheCalendarMirrorsTheBoard() {
        String ics = render(List.of(row(at("2026-10-01T09:00:00Z"), "Old", "Follow up")), "en");

        assertThat(ics).contains("SUMMARY:Old \u00b7 Follow up");
    }

    @Test
    void anApplicationWithoutACompanyIsNamedByItsRole() {
        String ics = render(List.of(row(at("2026-10-30T10:10:00Z"), null, "Data Analyst")), "en");

        assertThat(ics).contains("SUMMARY:Data Analyst\r\n");
    }

    @Test
    void commasSemicolonsBackslashesAndNewlinesAreEscaped() {
        String ics = render(
                List.of(row(at("2026-10-30T10:10:00Z"), "Smith, Jones; \\ Co", "Line\nTwo")), "en");

        assertThat(ics).contains("SUMMARY:Smith\\, Jones\\; \\\\ Co \u00b7 Line\\nTwo\r\n");
    }

    @Test
    void theAccountsLanguageNamesTheCalendarAndItsNote() {
        String english = render(List.of(), "en");
        String chinese = render(List.of(), "zh");

        assertThat(english).contains("X-WR-CALNAME:Career OS reminders\r\n");
        assertThat(english).contains("X-WR-CALDESC:Your application follow-ups from Career OS.\r\n");
        assertThat(chinese).contains("X-WR-CALNAME:\u804c\u4e1a\u63d0\u9192\r\n");
        assertThat(chinese).contains("X-WR-CALDESC:\u6765\u81ea Career OS \u7684\u7533\u8bf7\u63d0\u9192\u3002\r\n");
    }

    @Test
    void anAccountWithNothingScheduledStillGetsAParsableCalendar() {
        String ics = render(List.of(), "en");

        assertThat(ics).contains("VERSION:2.0\r\n", "CALSCALE:GREGORIAN\r\n");
        assertThat(ics).doesNotContain("BEGIN:VEVENT");
    }

    @Test
    void theStampIsTheRowsOwnLastChangeSoAPollDoesNotRewriteTheEvent() {
        String ics = render(List.of(row(at("2026-10-30T10:00:00Z"), "Acme", "Backend")), "en");

        assertThat(ics).contains("DTSTAMP:20261001T080000Z\r\n");
    }

    @Test
    void aRowTheDatabaseHasNotStampedFallsBackToItsCreationThenToTheReminder() {
        Application created = row(at("2026-10-30T10:00:00Z"), "Acme", "Backend");
        when(created.getUpdatedAt()).thenReturn(null);

        Application bare = row(at("2026-10-30T11:00:00Z"), "Acme", "Backend");
        when(bare.getUpdatedAt()).thenReturn(null);
        when(bare.getCreatedAt()).thenReturn(null);

        String ics = render(List.of(created, bare), "en");

        assertThat(ics).contains("DTSTAMP:20260930T070000Z\r\n");
        assertThat(ics).contains("DTSTAMP:20261030T110000Z\r\n");
    }

    @Test
    void aChineseTitleFoldsAtOctetBoundariesAndUnfoldsBackToItself() {
        String title = "\u5f88\u957f\u7684\u4e2d\u6587\u9762\u8bd5\u63d0\u9192".repeat(8);
        String ics = render(List.of(row(at("2026-10-30T10:00:00Z"), "\u5f88\u957f\u7684\u516c\u53f8\u540d\u79f0".repeat(6),
                title)), "zh");

        for (String physical : ics.split("\r\n")) {
            assertThat(physical.getBytes(StandardCharsets.UTF_8).length)
                    .as("physical line %s", physical)
                    .isLessThanOrEqualTo(75);
        }
        assertThat(ics).contains("\r\n ");
        assertThat(unfold(ics)).contains("SUMMARY:" + "\u5f88\u957f\u7684\u516c\u53f8\u540d\u79f0".repeat(6)
                + " \u00b7 " + title + "\r\n");
    }
}
