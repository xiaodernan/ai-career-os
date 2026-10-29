package com.careeros.calendar.service;

import java.nio.charset.StandardCharsets;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.UUID;

/**
 * The calendar document the reader's phone subscribes to (roadmap 34): RFC 5545, one VEVENT
 * per application that carries a reminder.
 *
 * <p>Three decisions the format does not make for us. The UID is the application id plus a
 * fixed suffix, so the event keeps its identity across regenerations and an edited reminder is
 * an update rather than a second event. DTSTAMP is the row's own last-modified time rather
 * than the moment of rendering, so an unchanged board produces a byte-identical document and a
 * calendar client can tell "nothing happened" from "something did". And the event is
 * transparent ({@code TRANSP:TRANSPARENT}): a follow-up reminder should not make the reader
 * look busy in somebody else's scheduling view.
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
     * The whole document. An account with no reminders gets a valid empty calendar rather than
     * an error: "nothing on the board has a time" is a normal answer a subscriber can hold.
     */
    public static String render(List<Reminder> reminders, String calendarName, String calendarNote,
                                String appUrl) {
        StringBuilder out = new StringBuilder();
        out.append("BEGIN:VCALENDAR\r\n");
        out.append("VERSION:2.0\r\n");
        out.append("PRODID:-//Career OS//Application reminders//EN\r\n");
        out.append("CALSCALE:GREGORIAN\r\n");
        out.append("METHOD:PUBLISH\r\n");
        text(out, "X-WR-CALNAME", calendarName);
        text(out, "X-WR-CALDESC", calendarNote);
        for (Reminder reminder : reminders) {
            event(out, reminder, appUrl);
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
        out.append("END:VEVENT\r\n");
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
