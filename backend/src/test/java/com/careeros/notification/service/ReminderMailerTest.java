package com.careeros.notification.service;

import static org.assertj.core.api.Assertions.assertThat;

import com.careeros.auth.service.EmailSender;
import com.careeros.mail.service.MailLinks;
import com.careeros.mail.service.MailList;
import com.careeros.notification.dto.NotificationDtos.NotificationItem;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;

/**
 * The reminder's readable half (roadmap 41.1).
 *
 * <p>What is pinned: the letter names each role that came due with a link to its card,
 * absolutely, because a mailbox cannot resolve a path; the five-row cap counts the rest; the
 * subject counts what came due without a number when there is one; the chrome follows the
 * account's language while the role and company pass through as the reader wrote them; and the
 * stop link names the reminders list, so turning this letter off does not silence the morning
 * one.
 */
class ReminderMailerTest {

    private static final UUID READER = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final MailLinks LINKS = new MailLinks("test-secret", "https://careeros.example");

    private static NotificationItem item(String title, String company) {
        return new NotificationItem("reminder:x:1", NotificationService.KIND_REMINDER, title,
                company, "applied", null, null, "/applications?application=" + title,
                OffsetDateTime.now(), false);
    }

    private final List<Map<String, String>> headers = new ArrayList<>();
    private final EmailSender email = (to, subject, body, extraHeaders) -> {
        headers.add(extraHeaders);
    };

    @Test
    void the_letter_names_the_role_the_company_and_its_card() {
        List<NotificationItem> due = List.of(item("Senior Analyst", "Acme"));

        String body = ReminderMailer.body(due, "en", "https://careeros.example",
                LINKS.page(READER));

        assertThat(ReminderMailer.subject(due.size(), "en"))
                .isEqualTo("Career OS: a reminder came due");
        assertThat(body).isEqualTo(
                "A reminder you set on your Career OS board has come due:\n\n"
                        + "- Senior Analyst at Acme\n"
                        + "  https://careeros.example/applications?application=Senior Analyst\n\n"
                        + "Move it, mark it done, or clear it on the board; the reminder waits "
                        + "there until you do.\n"
                        + "Stop these reminder letters: " + LINKS.page(READER) + "\n");
    }

    @Test
    void the_names_the_reader_left_blank_fall_back_the_way_the_inbox_does() {
        String body = ReminderMailer.body(List.of(item(null, "Acme"), item("", "")), "en",
                "https://careeros.example", LINKS.page(READER));

        assertThat(body).contains("- A role at Acme\n", "- An application\n");
    }

    @Test
    void a_crowded_minute_names_five_and_counts_the_rest() {
        List<NotificationItem> due = new ArrayList<>();
        for (int i = 0; i < 8; i++) {
            due.add(item("Role " + i, "Acme"));
        }

        String body = ReminderMailer.body(due, "en", "https://careeros.example",
                LINKS.page(READER));

        assertThat(ReminderMailer.subject(due.size(), "zh")).isEqualTo("Career OS：8 条提醒到期了");
        assertThat(body).contains("  ... and 3 more\n");
        assertThat(body).doesNotContain("Role 5");
    }

    @Test
    void a_chinese_account_reads_the_letter_in_chinese() {
        String body = ReminderMailer.body(List.of(item("高级分析师", "艾克米")), "zh",
                "https://careeros.example", LINKS.page(READER));

        assertThat(ReminderMailer.subject(1, "zh")).isEqualTo("Career OS：一条提醒到期了");
        assertThat(body).startsWith("你在 Career OS 看板上设的这条提醒到期了：").contains(
                "- 艾克米 的 高级分析师",
                "不想再收到提醒信：" + LINKS.page(READER));
    }

    @Test
    void a_letter_without_a_card_link_points_at_the_board_instead_of_nowhere() {
        NotificationItem noLink = new NotificationItem("reminder:x:2",
                NotificationService.KIND_REMINDER, "Senior Analyst", "Acme", "applied", null, null,
                null, OffsetDateTime.now(), false);

        String body = ReminderMailer.body(List.of(noLink), "en", "https://careeros.example/",
                LINKS.page(READER));

        assertThat(body).contains("  https://careeros.example/applications\n");
    }

    @Test
    void the_one_click_header_names_the_reminders_list_not_the_morning_one() {
        ReminderMailer mailer = new ReminderMailer(email, LINKS);

        mailer.send(READER, "reader@example.com", List.of(item("Senior Analyst", "Acme")), "en");

        assertThat(headers).containsExactly(
                LINKS.oneClick(READER, MailList.REMINDERS));
        assertThat(headers.get(0).get("List-Unsubscribe")).contains("/stop/reminders>");
    }
}
