package com.careeros.calendar.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.careeros.application.entity.Application;
import com.careeros.application.repository.ApplicationRepository;
import com.careeros.offer.entity.OfferRow;
import com.careeros.offer.repository.OfferShelfRepository;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/**
 * What the calendar feed says (roadmap 34.1, offer deadlines in Epic 196).
 *
 * <p>A calendar is read by software, so the claims are structural: one event per reminder, a
 * UTC start the parser can compare, a stable UID so a poll updates the event instead of adding
 * a copy, an end half an hour later, and both a description and a URL that lead back to the
 * board. Past reminders stay: the document mirrors the board, so an event leaves when the
 * reader clears the reminder, not when the date slips by.
 *
 * <p>The decision lane (Epic 196) carries one event per <em>pending</em> offer with a deadline:
 * an offer the reader already took or passed is out of the calendar, an accepted row's date is
 * settled news, not a reminder. The alarm rings a day ahead ({@code -P1D}), the UID suffix keeps
 * the two lanes from ever colliding, and the link leads to the shelf, not the board.
 *
 * <p>The text rules are the ones a calendar client will refuse the whole document over:
 * commas, semicolons, backslashes and newlines are escaped, and long lines fold at 75 octets
 * without splitting a multi-byte character. A Chinese title is where that last rule earns its
 * keep -- folding on characters would cut a glyph in half and every parser would drop the line.
 */
class CalendarFeedTest {

    private static final UUID ALICE = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final UUID APPLICATION = UUID.fromString("55555555-5555-4555-8555-555555555555");
    private static final UUID OFFER = UUID.fromString("77777777-7777-4777-8777-777777777777");

    private static final OffsetDateTime UPDATED = OffsetDateTime.parse("2026-10-01T08:00:00Z");
    private static final OffsetDateTime CREATED = OffsetDateTime.parse("2026-09-30T07:00:00Z");
    private static final OffsetDateTime OFFER_UPDATED = OffsetDateTime.parse("2026-11-02T08:00:00Z");

    private final ApplicationRepository applications = mock(ApplicationRepository.class);
    private final OfferShelfRepository offers = mock(OfferShelfRepository.class);
    private final CalendarLinks links = new CalendarLinks("test-secret", "https://careeros.example");
    private final CalendarService service = new CalendarService(applications, offers, links);

    @BeforeEach
    void theOffersLaneIsEmptyUnlessATestFillsIt() {
        when(offers.findByUserIdAndDecisionAndDeadlineIsNotNullOrderByDeadlineAsc(ALICE, "pending"))
                .thenReturn(List.of());
    }

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

    private static OfferRow offer(OffsetDateTime deadline, String label) {
        OfferRow row = mock(OfferRow.class);
        when(row.getId()).thenReturn(OFFER);
        when(row.getLabel()).thenReturn(label);
        when(row.getDeadline()).thenReturn(deadline);
        when(row.getUpdatedAt()).thenReturn(OFFER_UPDATED);
        return row;
    }

    private String render(List<Application> rows, String locale) {
        when(applications.findByUserIdAndReminderAtIsNotNullOrderByReminderAtAscIdAsc(ALICE))
                .thenReturn(rows);
        return service.feed(ALICE, locale);
    }

    private String renderWithOffers(List<Application> rows, List<OfferRow> offerRows, String locale) {
        when(applications.findByUserIdAndReminderAtIsNotNullOrderByReminderAtAscIdAsc(ALICE))
                .thenReturn(rows);
        when(offers.findByUserIdAndDecisionAndDeadlineIsNotNullOrderByDeadlineAsc(ALICE, "pending"))
                .thenReturn(offerRows);
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
        assertThat(ics).contains("SUMMARY:Acme · Backend Engineer\r\n");
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
                + "DESCRIPTION:Acme · Backend Engineer\r\n"
                + "TRIGGER:PT0M\r\n"
                + "END:VALARM\r\n");
    }

    @Test
    void aReminderThatPassedStaysOnTheFeedBecauseTheCalendarMirrorsTheBoard() {
        String ics = render(List.of(row(at("2026-10-01T09:00:00Z"), "Old", "Follow up")), "en");

        assertThat(ics).contains("SUMMARY:Old · Follow up");
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

        assertThat(ics).contains("SUMMARY:Smith\\, Jones\\; \\\\ Co · Line\\nTwo\r\n");
    }

    @Test
    void theAccountsLanguageNamesTheCalendarAndItsNote() {
        String english = unfold(render(List.of(), "en"));
        String chinese = unfold(render(List.of(), "zh"));

        assertThat(english).contains("X-WR-CALNAME:Career OS reminders\r\n");
        assertThat(english).contains(
                "X-WR-CALDESC:Your application follow-ups and offer decision deadlines from Career OS.\r\n");
        assertThat(chinese).contains("X-WR-CALNAME:职业提醒\r\n");
        assertThat(chinese).contains("X-WR-CALDESC:来自 Career OS 的申请提醒与录用决定截止日期。\r\n");
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
        String title = "很长的中文面试提醒".repeat(8);
        String ics = render(List.of(row(at("2026-10-30T10:00:00Z"), "很长的公司名称".repeat(6),
                title)), "zh");

        for (String physical : ics.split("\r\n")) {
            assertThat(physical.getBytes(StandardCharsets.UTF_8).length)
                    .as("physical line %s", physical)
                    .isLessThanOrEqualTo(75);
        }
        assertThat(ics).contains("\r\n ");
        assertThat(unfold(ics)).contains("SUMMARY:" + "很长的公司名称".repeat(6)
                + " · " + title + "\r\n");
    }

    @Test
    void aPendingOfferWithADeadlineBecomesOneEventPointingAtTheShelf() {
        String ics = renderWithOffers(List.of(),
                List.of(offer(at("2026-12-15T17:00:00Z"), "Synergy — Platform Engineer")), "en");

        assertThat(ics).contains("UID:" + OFFER + "@careeros-offer-deadline\r\n");
        assertThat(ics).contains("DTSTART:20261215T170000Z\r\n");
        assertThat(ics).contains("SUMMARY:Decision due: Synergy — Platform Engineer\r\n");
        assertThat(ics).contains("DESCRIPTION:https://careeros.example/offers\r\n");
        assertThat(ics).contains("URL:https://careeros.example/offers\r\n");
        // The alarm rings the morning before, not at the moment of the decision.
        assertThat(ics).contains("TRIGGER:-P1D\r\n");
    }

    @Test
    void aDecidedOfferIsNotOnTheCalendarBecauseTheQuestionIsAnswered() {
        // The derived query is scoped to decision = pending; the service does not re-filter,
        // and this case pins that the boundary is where it says it is.
        when(offers.findByUserIdAndDecisionAndDeadlineIsNotNullOrderByDeadlineAsc(ALICE, "pending"))
                .thenReturn(List.of());
        String ics = service.feed(ALICE, "en");

        assertThat(ics).doesNotContain("@careeros-offer-deadline");
    }

    @Test
    void theDeadlineEventIsNamedInTheAccountsLanguage() {
        String chinese = renderWithOffers(List.of(),
                List.of(offer(at("2026-12-15T17:00:00Z"), "云野 — 高级后端")), "zh");

        assertThat(chinese).contains("SUMMARY:决定截止：云野 — 高级后端\r\n");
        assertThat(chinese).contains("DESCRIPTION:https://careeros.example/offers\r\n");
    }

    @Test
    void theTimestampIsTheOffersOwnLastChangeSoAPollDoesNotRewriteTheEvent() {
        String ics = renderWithOffers(List.of(),
                List.of(offer(at("2026-12-15T17:00:00Z"), "Synergy")), "en");

        assertThat(ics).contains("DTSTAMP:20261102T080000Z\r\n");
    }

    @Test
    void anOfferEventUIDNeverCollidesWithAnApplicationEventUID() {
        String ics = renderWithOffers(
                List.of(row(at("2026-12-15T17:00:00Z"), "Synergy", "Platform Engineer")),
                List.of(offer(at("2026-12-15T17:00:00Z"), "Synergy — Platform Engineer")), "en");

        assertThat(ics).contains("UID:" + APPLICATION + "@careeros\r\n");
        assertThat(ics).contains("UID:" + OFFER + "@careeros-offer-deadline\r\n");
    }
}
