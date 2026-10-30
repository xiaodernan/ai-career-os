package com.careeros.notification.service;

import com.careeros.auth.service.EmailSender;
import com.careeros.mail.service.MailLinks;
import com.careeros.mail.service.MailList;
import com.careeros.notification.dto.NotificationDtos.NotificationItem;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Component;

/**
 * The reminder's own letter (roadmap 41.1): the moment a reminder comes due, the reader is told
 * outside the app rather than at the next morning's sweep.
 *
 * <p>The letter is short because the reminder is. It names the roles that came due, links each
 * to its card, and says the reminder waits on the board -- so the mailbox is a pointer and the
 * app is still the place a reminder is settled. A minute where five reminders fall due is a
 * letter naming five, and past that the rest are counted: a mailbox does not need a wall.
 *
 * <p>It speaks the account's language, like the morning letter, and its footer's stop link
 * names the reminders list, so a reader who finds this letter noise turns this letter off
 * without losing the morning one. The engine-written names (the role, the company) pass through
 * as stored: they are the reader's own data, not chrome.
 */
@Component
public class ReminderMailer {

    /** How many reminders one letter names before it starts counting. */
    static final int MAX_ROWS = 5;

    private static final String BOARD = "/applications";

    private static final Words EN = new Words(
            "Career OS: a reminder came due",
            "Career OS: {n} reminders came due",
            "A reminder you set on your Career OS board has come due:\n",
            "The reminders you set on your Career OS board have come due:\n",
            "An application",
            "A role at {company}",
            "{title} at {company}",
            "  ... and {n} more\n",
            "Move it, mark it done, or clear it on the board; the reminder waits there until you do.\n",
            "Stop these reminder letters: {url}\n");

    private static final Words ZH = new Words(
            "Career OS：一条提醒到期了",
            "Career OS：{n} 条提醒到期了",
            "你在 Career OS 看板上设的这条提醒到期了：\n",
            "你在 Career OS 看板上设的这些提醒到期了：\n",
            "一条投递",
            "{company} 的一个职位",
            "{company} 的 {title}",
            "  …… 另有 {n} 条\n",
            "在看板上把它挪走、标记完成或清掉；提醒会在那里一直等到你处理。\n",
            "不想再收到提醒信：{url}\n");

    private final EmailSender email;
    private final MailLinks links;

    public ReminderMailer(EmailSender email, MailLinks links) {
        this.email = email;
        this.links = links;
    }

    public void send(UUID userId, String to, List<NotificationItem> due, String locale) {
        email.send(to, subject(due.size(), locale),
                body(due, locale, links.webRoot(), links.page(userId)),
                links.oneClick(userId, MailList.REMINDERS));
    }

    /** The subject names the one fact a mailbox shows before the letter is opened: how many. */
    static String subject(int count, String locale) {
        Words words = wordsFor(locale);
        return count == 1 ? words.subjectOne() : fill(words.subjectMany(), "n", count);
    }

    /**
     * The letter: one line per reminder that came due, a link under each, the rest counted, and
     * the way out at the end. Links are absolute because a mailbox has no browser history.
     */
    static String body(List<NotificationItem> due, String locale, String baseUrl,
                       String settingsUrl) {
        Words words = wordsFor(locale);
        String root = baseUrl.endsWith("/") ? baseUrl.substring(0, baseUrl.length() - 1) : baseUrl;
        StringBuilder body = new StringBuilder();
        body.append(due.size() == 1 ? words.introOne() : words.introMany()).append('\n');
        due.stream().limit(MAX_ROWS).forEach(item -> {
            body.append("- ").append(role(words, item)).append('\n');
            String link = item.link() == null || item.link().isBlank() ? BOARD : item.link();
            body.append("  ").append(root).append(link).append("\n\n");
        });
        if (due.size() > MAX_ROWS) {
            body.append(fill(words.more(), "n", due.size() - MAX_ROWS));
        }
        body.append(words.action());
        body.append(fill(words.unsubscribe(), "url", settingsUrl));
        return body.toString();
    }

    private static Words wordsFor(String locale) {
        return "zh".equals(locale) ? ZH : EN;
    }

    /**
     * What the row is called in a mailbox: the same names the inbox screen shows, in the same
     * order, with the same fallbacks when a name is missing.
     */
    private static String role(Words words, NotificationItem item) {
        String title = text(item.title());
        String company = text(item.subject());
        if (title == null) {
            return company == null ? words.anApplication()
                    : fill(words.aRoleAt(), "company", company);
        }
        return company == null ? title
                : fill(fill(words.titleAtCompany(), "title", title), "company", company);
    }

    private static String fill(String pattern, String hole, Object value) {
        return pattern.replace("{" + hole + "}", String.valueOf(value));
    }

    private static String text(String value) {
        if (value == null) {
            return null;
        }
        String text = value.trim();
        return text.isEmpty() ? null : text;
    }

    /** One language's half of the letter; patterns carry named holes filled at render time. */
    record Words(
            String subjectOne,
            String subjectMany,
            String introOne,
            String introMany,
            String anApplication,
            String aRoleAt,
            String titleAtCompany,
            String more,
            String action,
            String unsubscribe) {
    }
}
