package com.careeros.report.service;

import com.careeros.auth.service.EmailSender;
import com.careeros.report.entity.WeeklyDigest;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import org.springframework.stereotype.Component;

/**
 * The weekly letter's readable half (roadmap 21.2): the filed digest turned into a plain-text
 * mail and handed to whichever transport {@code app.email.provider} armed.
 *
 * <p>The body is assembled from the payload the engine answered, never from fresh numbers, so
 * the copy in the mailbox and the copy on the dashboard cannot disagree about the week. A key
 * the payload does not carry drops its line instead of printing a zero the engine never said.
 * The wording is English because the sweep composes without a reader's language, which is also
 * why the engine's signals arrive in its default language.
 */
@Component
public class WeeklyDigestMailer {

    /** A mailbox is not a dashboard: this many stalled rows are listed, the rest are counted. */
    static final int MAX_STALLED_ROWS = 10;

    private static final DateTimeFormatter WEEK =
            DateTimeFormatter.ofPattern("d MMMM uuuu", Locale.ENGLISH);
    private static final DateTimeFormatter SHORT_WEEK =
            DateTimeFormatter.ofPattern("d MMM uuuu", Locale.ENGLISH);

    private final EmailSender email;

    public WeeklyDigestMailer(EmailSender email) {
        this.email = email;
    }

    public void send(String to, WeeklyDigest letter) {
        email.send(to, subject(letter.getWeekStart()), letterBody(letter.getWeekStart(), letter.getPayload()));
    }

    /** The subject names the week, so a mailbox sorted by subject still reads as a series. */
    static String subject(LocalDate weekStart) {
        return "Your week in applications (" + weekStart.format(SHORT_WEEK) + ")";
    }

    /** The letter's body: the payload laid out, one line per reading it carries. */
    static String letterBody(LocalDate weekStart, Map<String, Object> payload) {
        StringBuilder body = new StringBuilder();
        body.append("Week of ").append(weekStart.format(WEEK)).append(".\n");

        Long total = number(payload.get("totalApplications"));
        Long active = number(payload.get("activePipeline"));
        if (total != null) {
            body.append("\nApplications on the board: ").append(total);
            if (active != null) {
                body.append(" (").append(active).append(" active)");
            }
            body.append('\n');
        }

        Map<String, Object> mix = object(payload.get("stageCounts"));
        if (!mix.isEmpty()) {
            StringBuilder line = new StringBuilder();
            for (Map.Entry<String, Object> stage : mix.entrySet()) {
                if (line.length() > 0) {
                    line.append(", ");
                }
                line.append(stage.getKey()).append(' ').append(stage.getValue());
            }
            body.append("Stage mix: ").append(line).append('\n');
        }

        List<String> rates = new ArrayList<>();
        Double response = decimal(payload.get("responseRate"));
        if (response != null) {
            rates.add("Response rate: " + percent(response));
        }
        Double offer = decimal(payload.get("offerRate"));
        if (offer != null) {
            rates.add("Offer rate: " + percent(offer));
        }
        if (!rates.isEmpty()) {
            body.append(String.join(" | ", rates)).append('\n');
        }

        Long stalledCount = number(payload.get("stalledCount"));
        if (stalledCount != null && stalledCount > 0) {
            Long window = number(payload.get("windowDays"));
            body.append("\nStalled");
            if (window != null) {
                body.append(" - no movement in ").append(window).append("+ days");
            }
            body.append(": ").append(stalledCount).append('\n');
            List<Map<String, Object>> stalled = rows(payload.get("stalled"));
            stalled.stream().limit(MAX_STALLED_ROWS).forEach(row -> {
                body.append("  - ").append(where(row));
                Long days = number(row.get("daysSinceLastActivity"));
                if (days != null) {
                    body.append(" (").append(days).append(" days)");
                }
                body.append('\n');
            });
            if (stalled.size() > MAX_STALLED_ROWS) {
                body.append("  ... and ").append(stalled.size() - MAX_STALLED_ROWS).append(" more\n");
            }
        }

        List<String> signals = strings(payload.get("signals"));
        if (!signals.isEmpty()) {
            body.append("\nWhat the week says:\n");
            for (String signal : signals) {
                body.append("  - ").append(signal).append('\n');
            }
        }

        return body.toString();
    }

    private static String where(Map<String, Object> row) {
        String title = text(row.get("title"));
        String company = text(row.get("company"));
        if (title == null) {
            return company == null ? "An application" : "A role at " + company;
        }
        return company == null ? title : title + " at " + company;
    }

    private static String percent(Double rate) {
        return Math.round(rate * 100) + "%";
    }

    private static Long number(Object value) {
        return value instanceof Number n ? n.longValue() : null;
    }

    private static Double decimal(Object value) {
        return value instanceof Number n ? n.doubleValue() : null;
    }

    private static String text(Object value) {
        if (value == null) {
            return null;
        }
        String text = value.toString().trim();
        return text.isEmpty() ? null : text;
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> object(Object value) {
        return value instanceof Map<?, ?> map ? (Map<String, Object>) map : Map.of();
    }

    @SuppressWarnings("unchecked")
    private static List<Map<String, Object>> rows(Object value) {
        return value instanceof List<?> list ? (List<Map<String, Object>>) list : List.of();
    }

    private static List<String> strings(Object value) {
        if (!(value instanceof List<?> list)) {
            return List.of();
        }
        return list.stream().filter(Objects::nonNull).map(Object::toString).toList();
    }
}
