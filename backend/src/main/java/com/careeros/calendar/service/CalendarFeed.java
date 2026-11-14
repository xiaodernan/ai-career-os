package com.careeros.calendar.service;

import java.nio.charset.StandardCharsets;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.UUID;

/**
 * The calendar document the reader's phone subscribes to (roadmap 34, offer deadlines in
 * Epic 196): RFC 5545, one VEVENT per application that carries a reminder, one per pending
 * offer that carries a deadline.
 *
 * <p>Three decisions the format does not make for us. The UID is the row id plus a fixed suffix
 * per lane, so the event keeps its identity across regenerations and an edited reminder or a
 * moved deadline is an update rather than a second event. DTSTAMP is the row's own
 * last-modified time rather than the moment of rendering, so an unchanged board produces a
 * byte-identical document and a calendar client can tell "nothing happened" from "something
 * did". And the event is transparent ({@code TRANSP:TRANSPARENT}): a follow-up reminder or a
 * decision day should not make the reader look busy in somebody else's scheduling view.
 *
 * <p>Each event also carries its own alarm (roadmap 35.2), a DISPLAY {@code VALARM} triggered at
 * the event's start for applications, and one day ahead ({@code -P1D}) for an offer deadline —
 * a decision deserves a morning of notice rather than the moment of the deadline.
 *
 * <p>Text values are escaped and every content line is folded at 75 octets, counting UTF-8
 * bytes rather than characters, so a company name in Chinese folds where RFC 5545 says it
 * should instead of cutting a character in half.
 */
public final class CalendarFeed {

    private static final DateTimeFormatter UTC = DateTimeFormatter
            .ofPattern("yyyyMMdd'T'HHmmss'Z'")
            .withZone(ZoneOffset.UTC);

    /** The longest physical line RFC 5545 allows, counting the continuation's leading space. */
    private static final int FOLD_AT = 75;

    /** How long an event occupies the calendar; a reminder is a moment, shown as half an hour. */
    private static final int EVENT_MINUTES = 30;

    private CalendarFeed() {
    }

    /** One row's worth of an event: everything the feed may say about an application. */
    public record Reminder(UUID id, String title, String company, OffsetDateTime at,
                           OffsetDateTime stamp) {
    }

    /**
     * One pending offer's decision day. Only pending offers reach this record: the calendar
     * carries the decision that is still open, so an offer the reader already took or passed
     * leaves the calendar instead of ringing about a settled case. The label is the shelf's
     * own wording ("Acme — Senior Backend"), kept verbatim so the event reads like the row.
     */
    public record Deadline(UUID id, String label, OffsetDateTime at, OffsetDateTime stamp) {
    }

    /**
     * The whole document. An account with no reminders and no deadlines gets a valid empty
     * calendar rather than an error: "nothing on the board has a time" is a normal answer a
     * subscriber can hold.
     */
    public static String render(List<Reminder> reminders, List<Deadline> deadlines,
                                String calendarName, String calendarNote,
                                String appUrl, String offersUrl, boolean chinese) {
        StringBuilder out = new StringBuilder();
        out.append("BEGIN:VCALENDAR\r\n");
        out.append("VERSION:2.0\r\n");
        out.append("PRODID:-//Career OS//Application reminders and offer deadlines//EN\r\n");
        out.append("CALSCALE:GREGORIAN\r\n");
        out.append("METHOD:PUBLISH\r\n");
        text(out, "X-WR-CALNAME", calendarName);
        text(out, "X-WR-CALDESC", calendarNote);
        if (deadlines == null) {
            deadlines = List.of();
        }
        for (Reminder reminder : reminders) {
            event(out, reminder, appUrl);
        }
        for (Deadline deadline : deadlines) {
            deadlineEvent(out, deadline, offersUrl, chinese);
        }
        out.append("END:VCALENDAR\r\n");
        return out.toString();
    }

    private static void event(StringBuilder out, Reminder reminder, String appUrl) {
        out.append("BEGIN:VEVENT\r\n");
        raw(out, "UID", reminder.id() + "@careeros");
        raw(out, "DTSTAMP", UTC.format(reminder.stamp()));
        raw(out, "DTSTART", UTC.format(reminder.at()));
        raw(out, "DTEND", UTC.format(reminder.at().plusMinutes(EVENT_MINUTES)));
        text(out, "SUMMARY", summary(reminder));
        text(out, "DESCRIPTION", appUrl);
        raw(out, "URL", appUrl);
        out.append("STATUS:CONFIRMED\r\n");
        out.append("TRANSP:TRANSPARENT\r\n");
        out.append("BEGIN:VALARM\r\n");
        out.append("ACTION:DISPLAY\r\n");
        text(out, "DESCRIPTION", summary(reminder));
        out.append("TRIGGER:PT0M\r\n");
        out.append("END:VALARM\r\n");
        out.append("END:VEVENT\r\n");
    }

    private static void deadlineEvent(StringBuilder out, Deadline deadline, String offersUrl,
                                      boolean chinese) {
        // A day, not a moment: the deadline wakes the reader the morning before it, and the
        // event sits on the calendar as the decision's own anchor. The UID suffix keeps the
        // two lanes from ever colliding on an id.
        String summary = chinese ? "决定截止：" + trimTo(deadline.label())
                                 : "Decision due: " + trimTo(deadline.label());
        out.append("BEGIN:VEVENT\r\n");
        raw(out, "UID", deadline.id() + "@careeros-offer-deadline");
        raw(out, "DTSTAMP", UTC.format(deadline.stamp()));
        raw(out, "DTSTART", UTC.format(deadline.at()));
        raw(out, "DTEND", UTC.format(deadline.at().plusMinutes(EVENT_MINUTES)));
        text(out, "SUMMARY", summary);
        text(out, "DESCRIPTION", offersUrl);
        raw(out, "URL", offersUrl);
        out.append("STATUS:CONFIRMED\r\n");
        out.append("TRANSP:TRANSPARENT\r\n");
        out.append("BEGIN:VALARM\r\n");
        out.append("ACTION:DISPLAY\r\n");
        text(out, "DESCRIPTION", summary);
        out.append("TRIGGER:-P1D\r\n");
        out.append("END:VALARM\r\n");
        out.append("END:VEVENT\r\n");
    }

    /** The shelf stores up to 120 chars; so does everything else, the feed included. */
    private static String trimTo(String value) {
        return value == null ? "" : value.trim();
    }

    /** "Company · Role", or the role alone when the row never had a company. */
    private static String summary(Reminder reminder) {
        String title = reminder.title() == null ? "" : reminder.title().trim();
        String company = reminder.company() == null ? "" : reminder.company().trim();
        if (company.isEmpty()) {
            return title;
        }
        return title.isEmpty() ? company : company + " · " + title;
    }

    /** A machine value, written as it is: dates, ids and URLs have no characters to escape. */
    private static void raw(StringBuilder out, String name, String value) {
        fold(out, name + ":" + value);
    }

    /** A human value, escaped the way RFC 5545 section 3.3.11 says. */
    private static void text(StringBuilder out, String name, String value) {
        fold(out, name + ":" + escape(value));
    }

    /**
     * Backslash, semicolon and comma are the three characters a text value must escape;
     * a line break becomes the two characters {@code \n}, which a client renders as a break.
     */
    private static String escape(String value) {
        if (value == null) {
            return "";
        }
        StringBuilder out = new StringBuilder(value.length());
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            switch (c) {
                case '\\' -> out.append("\\\\");
                case ';' -> out.append("\\;");
                case ',' -> out.append("\\,");
                case '\r' -> {
                    if (i + 1 < value.length() && value.charAt(i + 1) == '\n') {
                        i++;
                    }
                    out.append("\\n");
                }
                case '\n' -> out.append("\\n");
                default -> out.append(c);
            }
        }
        return out.toString();
    }

    /**
     * Writes one content line, folded at 75 octets. A continuation starts with one space and
     * that space counts against the limit; code points are never split, so the fold lands
     * between characters even where every character costs more than one octet.
     */
    private static void fold(StringBuilder out, String line) {
        int used = 0;
        for (int i = 0; i < line.length(); ) {
            int codePoint = line.codePointAt(i);
            int chars = Character.charCount(codePoint);
            String piece = line.substring(i, i + chars);
            int octets = octets(piece);
            if (used + octets > FOLD_AT) {
                out.append("\r\n ");
                used = 1;
            }
            out.append(piece);
            used += octets;
            i += chars;
        }
        out.append("\r\n");
    }

    private static int octets(String piece) {
        return piece.getBytes(StandardCharsets.UTF_8).length;
    }
}
