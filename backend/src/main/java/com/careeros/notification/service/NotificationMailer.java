package com.careeros.notification.service;

import com.careeros.auth.service.EmailSender;
import com.careeros.mail.service.MailLinks;
import com.careeros.mail.service.MailList;
import com.careeros.notification.dto.NotificationDtos.NotificationItem;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Component;

/**
 * The inbox's readable half (roadmap 22.1): the signals still waiting in the app turned into a
 * plain-text mail and handed to whichever transport {@code app.email.provider} armed.
 *
 * <p>The letter is a pointer, not a second inbox. It names what is waiting, one line per
 * signal, and links back to the screen that can act on it; settling an item in the app is what
 * makes it stop. Ten rows is what a mailbox reads before it becomes a wall, so the rest are
 * counted rather than listed -- they were still announced, which is why the sweep latches every
 * item the letter was given, not only the ten it named.
 *
 * <p>The letter speaks the reader's language, because the account does (roadmap 21.4): the
 * subject, the labels and the sentences are drawn from {@link Words} in the same language the
 * inbox screen is read in. The engine-written signal text (an application's title, a feed's
 * name, a transport's error) is passed through as stored -- it belongs to the reader's own data,
 * not to the chrome.
 */
@Component
public class NotificationMailer {

    /** How many signals the letter names before it starts counting. */
    static final int MAX_ROWS = 10;

    private static final Words EN = new Words(
            "Career OS: a signal is waiting in your inbox",
            "Career OS: {n} signals are waiting in your inbox",
            "Signals waiting in your Career OS inbox:\n",
            " — ",
            "a reminder you set has come due",
            "no movement for {n}+ days",
            "last night's pull failed",
            "last night's pull proposed a new posting",
            "last night's pull proposed {n} new postings",
            "a new posting matches this saved search",
            "{n} new postings match this saved search",
            "An application",
            "A role at {company}",
            "{title} at {company}",
            "A scheduled pull",
            "A saved search",
            "  ... and {n} more\n",
            "Reading or acting in the app settles these, and a signal is mailed at most once.\n",
            "Stop these letters: {url}\n");

    private static final Words ZH = new Words(
            "Career OS：收件箱里有 {n} 条待看的信号",
            "Career OS：收件箱里有 {n} 条待看的信号",
            "收件箱里等你处理的信号：\n",
            " —— ",
            "你设置的提醒已经到期",
            "{n} 天以上没有动静",
            "昨晚的抓取失败了",
            "昨晚的抓取带来了 1 个新职位",
            "昨晚的抓取带来了 {n} 个新职位",
            "有 1 个新职位符合这个保存的搜索",
            "有 {n} 个新职位符合这个保存的搜索",
            "一条投递",
            "{company} 的一个职位",
            "{company} 的 {title}",
            "一次定时抓取",
            "一个保存的搜索",
            "  …… 另有 {n} 条\n",
            "在应用里读过或处理之后，这条信号就会安静下来；同一条信号最多寄一次。\n",
            "不想再收到这些信：{url}\n");

    private final EmailSender email;
    private final MailLinks links;

    public NotificationMailer(EmailSender email, MailLinks links) {
        this.email = email;
        this.links = links;
    }

    public void send(UUID userId, String to, List<NotificationItem> items, String locale) {
        email.send(to, subject(items.size(), locale),
                body(items, locale, links.webRoot(), links.page(userId)),
                links.oneClick(userId, MailList.SIGNALS));
    }

    /**
     * The subject counts what is waiting, because that is the one fact a mailbox can show
     * before the letter is opened. The count never says zero: the sweep only writes a letter
     * when something is waiting.
     */
    static String subject(int count, String locale) {
        Words words = wordsFor(locale);
        return count == 1 ? fill(words.subjectOne(), "n", count)
                : fill(words.subjectMany(), "n", count);
    }

    /**
     * The letter itself: one line per waiting signal, a link under each, the rest counted, and
     * the way out at the end. The item links are absolute because a mailbox has no browser
     * history to resolve a path against; the last line goes to the read-only settings page,
     * which is why a scanner that opens it changes nothing.
     */
    static String body(List<NotificationItem> items, String locale, String baseUrl, String settingsUrl) {
        Words words = wordsFor(locale);
        String root = baseUrl.endsWith("/") ? baseUrl.substring(0, baseUrl.length() - 1) : baseUrl;
        StringBuilder body = new StringBuilder();
        body.append(words.intro()).append('\n');
        items.stream().limit(MAX_ROWS).forEach(item -> {
            String sentence = sentence(words, item);
            body.append("- ").append(headline(words, item));
            if (!sentence.isEmpty()) {
                body.append(words.dash()).append(sentence);
            }
            body.append('\n');
            if (item.note() != null && !item.note().isBlank()) {
                body.append("  ").append(item.note().trim()).append('\n');
            }
            if (item.link() != null && !item.link().isBlank()) {
                body.append("  ").append(root).append(item.link()).append('\n');
            }
            body.append('\n');
        });
        if (items.size() > MAX_ROWS) {
            body.append(fill(words.more(), "n", items.size() - MAX_ROWS));
        }
        body.append(words.footer());
        body.append(fill(words.unsubscribe(), "url", settingsUrl));
        return body.toString();
    }

    private static Words wordsFor(String locale) {
        return "zh".equals(locale) ? ZH : EN;
    }

    /**
     * What the row is called in a mailbox: the names the inbox screen already shows, in the
     * language's own order, with the same fallbacks the screen uses when a name is missing.
     */
    private static String headline(Words words, NotificationItem item) {
        String title = text(item.title());
        String subject = text(item.subject());
        if (NotificationService.KIND_REMINDER.equals(item.kind())
                || NotificationService.KIND_STALE.equals(item.kind())) {
            if (title == null) {
                return subject == null ? words.anApplication()
                        : fill(words.aRoleAt(), "company", subject);
            }
            return subject == null ? title
                    : fill(fill(words.titleAtCompany(), "title", title), "company", subject);
        }
        if (NotificationService.KIND_SAVED_SEARCH.equals(item.kind())) {
            return title == null ? words.aSearch() : title;
        }
        return title == null ? words.aFeed() : title;
    }

    /** Why the signal is in the letter, in one sentence of the letter's language. */
    private static String sentence(Words words, NotificationItem item) {
        return switch (item.kind()) {
            case NotificationService.KIND_REMINDER -> words.reminder();
            case NotificationService.KIND_STALE -> fill(words.stale(), "n", NotificationService.STALE_DAYS);
            case NotificationService.KIND_INGESTION_FAILED -> words.ingestionFailed();
            case NotificationService.KIND_INGESTION_CREATED -> {
                Integer count = item.count();
                yield count == null || count == 1 ? words.ingestionCreatedOne()
                        : fill(words.ingestionCreatedMany(), "n", count);
            }
            case NotificationService.KIND_SAVED_SEARCH -> {
                Integer count = item.count();
                yield count == null || count == 1 ? words.savedSearchOne()
                        : fill(words.savedSearchMany(), "n", count);
            }
            default -> "";
        };
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

    /**
     * One language's half of the letter. The patterns carry named holes filled at render time;
     * the counts that read badly as digits in English -- a lone reminder, a lone posting, a
     * lone match -- have their own wordless singulars, while Chinese lets one pattern carry
     * the number.
     */
    record Words(
            String subjectOne,
            String subjectMany,
            String intro,
            String dash,
            String reminder,
            String stale,
            String ingestionFailed,
            String ingestionCreatedOne,
            String ingestionCreatedMany,
            String savedSearchOne,
            String savedSearchMany,
            String anApplication,
            String aRoleAt,
            String titleAtCompany,
            String aFeed,
            String aSearch,
            String more,
            String footer,
            String unsubscribe) {
    }
}
