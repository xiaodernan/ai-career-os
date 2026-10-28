package com.careeros.report.service;

import com.careeros.auth.service.EmailSender;
import com.careeros.mail.service.MailLinks;
import com.careeros.mail.service.MailList;
import com.careeros.report.entity.WeeklyDigest;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;
import org.springframework.stereotype.Component;

/**
 * The weekly letter's readable half (roadmap 21.2): the filed digest turned into a plain-text
 * mail and handed to whichever transport {@code app.email.provider} armed.
 *
 * <p>The body is assembled from the payload the engine answered, never from fresh numbers, so
 * the copy in the mailbox and the copy on the dashboard cannot disagree about the week. A key
 * the payload does not carry drops its line instead of printing a zero the engine never said.
 *
 * <p>The letter speaks the language it was written in (roadmap 21.4). The row froze that
 * language beside the payload, whose signals the engine already wrote in it, so the chrome --
 * the subject, the labels, the date -- is drawn from the same language rather than left in
 * English around Chinese sentences. The two vocabularies are {@link Words} values here: the
 * only place the backend authors prose for a reader.
 */
@Component
public class WeeklyDigestMailer {

    /** A mailbox is not a dashboard: this many stalled rows are listed, the rest are counted. */
    static final int MAX_STALLED_ROWS = 10;

    private static final DateTimeFormatter EN_WEEK =
            DateTimeFormatter.ofPattern("d MMMM uuuu", Locale.ENGLISH);
    private static final DateTimeFormatter EN_SHORT_WEEK =
            DateTimeFormatter.ofPattern("d MMM uuuu", Locale.ENGLISH);
    private static final DateTimeFormatter ZH_WEEK =
            DateTimeFormatter.ofPattern("uuuu年M月d日", Locale.CHINA);

    private static final Map<String, String> ZH_STAGES = Map.of(
            "saved", "已收藏",
            "applied", "已投递",
            "oa", "在线测评",
            "interview", "面试",
            "final_round", "终面",
            "offer", "录用",
            "rejected", "已拒绝");

    private static final Words EN = new Words(
            "Your week in applications ({date})",
            "Week of {date}.",
            "\nApplications on the board: {n}",
            " ({n} active)",
            "Stage mix: {list}\n",
            ", ",
            "Response rate: {pct}",
            "Offer rate: {pct}",
            " | ",
            "Stalled",
            " - no movement in {n}+ days",
            ": {n}",
            "\n",
            " ({n} days)",
            "  ... and {n} more\n",
            "\nWhat the week says:\n",
            "An application",
            "A role at {company}",
            "{title} at {company}",
            Map.of(),
            EN_WEEK,
            EN_SHORT_WEEK,
            "Stop these letters: {url}\n");

    private static final Words ZH = new Words(
            "你的求职周报（{date}）",
            "{date} 这一周。",
            "\n板上投递：{n}",
            "（进行中 {n}）",
            "阶段分布：{list}\n",
            "、",
            "回复率 {pct}",
            "录取率 {pct}",
            " | ",
            "停滞",
            " —— {n} 天以上没有动静",
            "：{n}",
            "\n",
            "（{n} 天）",
            "  …… 另有 {n} 条\n",
            "\n这一周告诉我们：\n",
            "一条投递",
            "{company} 的一个职位",
            "{company} 的 {title}",
            ZH_STAGES,
            ZH_WEEK,
            ZH_WEEK,
            "不想再收到这些信：{url}\n");

    private final EmailSender email;
    private final MailLinks links;

    public WeeklyDigestMailer(EmailSender email, MailLinks links) {
        this.email = email;
        this.links = links;
    }

    public void send(String to, WeeklyDigest letter) {
        UUID userId = letter.getUserId();
        email.send(to, subject(letter.getWeekStart(), letter.getLocale()),
                letterBody(letter.getWeekStart(), letter.getPayload(), letter.getLocale(),
                        links.page(userId)),
                links.oneClick(userId, MailList.WEEKLY));
    }

    /** The subject names the week, so a mailbox sorted by subject still reads as a series. */
    static String subject(LocalDate weekStart, String locale) {
        Words words = wordsFor(locale);
        return fill(words.subject(), "date", weekStart.format(words.shortWeek()));
    }

    /**
     * The letter's body: the payload laid out, one line per reading it carries, in the
     * language the letter was written in, with the way out at the end.
     */
    static String letterBody(LocalDate weekStart, Map<String, Object> payload, String locale,
                             String settingsUrl) {
        Words words = wordsFor(locale);
        StringBuilder body = new StringBuilder();
        body.append(fill(words.weekOf(), "date", weekStart.format(words.week()))).append('\n');

        Long total = number(payload.get("totalApplications"));
        Long active = number(payload.get("activePipeline"));
        if (total != null) {
            body.append(fill(words.onBoard(), "n", total));
            if (active != null) {
                body.append(fill(words.active(), "n", active));
            }
            body.append('\n');
        }

        Map<String, Object> mix = object(payload.get("stageCounts"));
        if (!mix.isEmpty()) {
            StringBuilder line = new StringBuilder();
            for (Map.Entry<String, Object> stage : mix.entrySet()) {
                if (line.length() > 0) {
                    line.append(words.stageSeparator());
                }
                line.append(words.stages().getOrDefault(stage.getKey(), stage.getKey()))
                        .append(' ').append(stage.getValue());
            }
            body.append(fill(words.stageMix(), "list", line));
        }

        List<String> rates = new ArrayList<>();
        Double response = decimal(payload.get("responseRate"));
        if (response != null) {
            rates.add(fill(words.responseRate(), "pct", percent(response)));
        }
        Double offer = decimal(payload.get("offerRate"));
        if (offer != null) {
            rates.add(fill(words.offerRate(), "pct", percent(offer)));
        }
        if (!rates.isEmpty()) {
            body.append(String.join(words.ratesSeparator(), rates)).append('\n');
        }

        Long stalledCount = number(payload.get("stalledCount"));
        if (stalledCount != null && stalledCount > 0) {
            Long window = number(payload.get("windowDays"));
            body.append(words.lineBreak()).append(words.stalled());
            if (window != null) {
                body.append(fill(words.stalledWindow(), "n", window));
            }
            body.append(fill(words.stalledCount(), "n", stalledCount)).append('\n');
            List<Map<String, Object>> stalled = rows(payload.get("stalled"));
            stalled.stream().limit(MAX_STALLED_ROWS).forEach(row -> {
                body.append("  - ").append(where(words, row));
                Long days = number(row.get("daysSinceLastActivity"));
                if (days != null) {
                    body.append(fill(words.days(), "n", days));
                }
                body.append('\n');
            });
            if (stalled.size() > MAX_STALLED_ROWS) {
                body.append(fill(words.more(), "n", stalled.size() - MAX_STALLED_ROWS));
            }
        }

        List<String> signals = strings(payload.get("signals"));
        if (!signals.isEmpty()) {
            body.append(words.signals());
            for (String signal : signals) {
                body.append("  - ").append(signal).append('\n');
            }
        }

        body.append(fill(words.unsubscribe(), "url", settingsUrl));
        return body.toString();
    }

    private static Words wordsFor(String locale) {
        return "zh".equals(locale) ? ZH : EN;
    }

    private static String where(Words words, Map<String, Object> row) {
        String title = text(row.get("title"));
        String company = text(row.get("company"));
        if (title == null) {
            return company == null ? words.anApplication() : fill(words.aRoleAt(), "company", company);
        }
        return company == null ? title
                : fill(fill(words.titleAtCompany(), "title", title), "company", company);
    }

    private static String percent(Double rate) {
        return Math.round(rate * 100) + "%";
    }

    private static String fill(String pattern, String hole, Object value) {
        return pattern.replace("{" + hole + "}", String.valueOf(value));
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

    /**
     * One language's half of the letter. The patterns carry named holes filled at render time;
     * {@code stages} renames the board's status values for the mailbox, and a value the table
     * does not know keeps its own name rather than disappearing.
     */
    record Words(
            String subject,
            String weekOf,
            String onBoard,
            String active,
            String stageMix,
            String stageSeparator,
            String responseRate,
            String offerRate,
            String ratesSeparator,
            String stalled,
            String stalledWindow,
            String stalledCount,
            String lineBreak,
            String days,
            String more,
            String signals,
            String anApplication,
            String aRoleAt,
            String titleAtCompany,
            Map<String, String> stages,
            DateTimeFormatter week,
            DateTimeFormatter shortWeek,
            String unsubscribe) {
    }
}
