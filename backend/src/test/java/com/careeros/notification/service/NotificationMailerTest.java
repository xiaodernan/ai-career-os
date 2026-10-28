package com.careeros.notification.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

import com.careeros.auth.service.EmailSender;
import com.careeros.notification.dto.NotificationDtos.NotificationItem;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

/**
 * The signal mail's readable half (roadmap 22.1).
 *
 * <p>What is pinned: the letter names each waiting signal in one line and links to the screen
 * that can act on it, absolutely, because a mailbox cannot resolve a path; the ten-row cap
 * counts the rest instead of mailing a wall; the subject counts what is waiting and says it
 * without a number when there is one; and the chrome follows the account's language while the
 * signal's own names pass through as the reader wrote them.
 */
class NotificationMailerTest {

    private static NotificationItem item(String kind, String title, String subject, Integer count,
                                         String note, String link) {
        return new NotificationItem("key-" + kind + "-" + title, kind, title, subject, "applied",
                count, note, link, OffsetDateTime.now(), false);
    }

    private static NotificationItem reminder() {
        return item(NotificationService.KIND_REMINDER, "Senior Analyst", "Acme", null, null,
                "/applications?application=app-1");
    }

    private static NotificationItem stale() {
        return item(NotificationService.KIND_STALE, "Data Analyst", "Globex", null, null,
                "/applications?application=app-2");
    }

    @Test
    void the_letter_names_each_waiting_signal_and_links_to_it() {
        List<NotificationItem> waiting = List.of(reminder(), stale(),
                item(NotificationService.KIND_INGESTION_FAILED, "Hiring board", "", null,
                        "Feed answered HTTP 503", "/ingestion"),
                item(NotificationService.KIND_INGESTION_CREATED, "Hiring board", "", 3, null,
                        "/ingestion"));

        String body = NotificationMailer.body(waiting, "en", "https://careeros.example");

        assertThat(NotificationMailer.subject(waiting.size(), "en"))
                .isEqualTo("Career OS: 4 signals are waiting in your inbox");
        assertThat(body).contains(
                "Signals waiting in your Career OS inbox:",
                "- Senior Analyst at Acme — a reminder you set has come due",
                "  https://careeros.example/applications?application=app-1",
                "- Data Analyst at Globex — no movement for 14+ days",
                "- Hiring board — last night's pull failed",
                "  Feed answered HTTP 503",
                "  https://careeros.example/ingestion",
                "- Hiring board — last night's pull proposed 3 new postings",
                "a signal is mailed at most once");
    }

    @Test
    void one_signal_is_named_in_the_singular() {
        List<NotificationItem> waiting = List.of(
                item(NotificationService.KIND_INGESTION_CREATED, "Hiring board", "", 1, null,
                        "/ingestion"));

        String body = NotificationMailer.body(waiting, "en", "http://localhost:3000");

        assertThat(NotificationMailer.subject(waiting.size(), "en"))
                .isEqualTo("Career OS: a signal is waiting in your inbox");
        assertThat(body).contains("- Hiring board — last night's pull proposed a new posting");
        assertThat(body).doesNotContain("1 new posting");
    }

    @Test
    void a_long_waiting_list_is_capped_and_the_rest_counted() {
        List<NotificationItem> waiting = new ArrayList<>();
        for (int i = 1; i <= 13; i++) {
            waiting.add(item(NotificationService.KIND_STALE, "Role " + i, "Acme", null, null,
                    "/applications?application=app-" + i));
        }

        String body = NotificationMailer.body(waiting, "en", "http://localhost:3000");

        assertThat(body).contains("Role 10", "  ... and 3 more");
        assertThat(body).doesNotContain("Role 11");
    }

    @Test
    void a_missing_name_still_gets_a_line() {
        List<NotificationItem> waiting = List.of(
                item(NotificationService.KIND_REMINDER, "", "Acme", null, null, "/applications"),
                item(NotificationService.KIND_REMINDER, "", "", null, null, "/applications"),
                item(NotificationService.KIND_INGESTION_FAILED, "", "", null, "boom", "/ingestion"));

        String body = NotificationMailer.body(waiting, "en", "http://localhost:3000");

        assertThat(body).contains("- A role at Acme — a reminder you set has come due",
                "- An application — a reminder you set has come due",
                "- A scheduled pull — last night's pull failed");
    }

    @Test
    void a_chinese_letter_speaks_chinese_around_the_readers_own_names() {
        List<NotificationItem> waiting = List.of(reminder(), stale(),
                item(NotificationService.KIND_INGESTION_FAILED, "Hiring board", "", null,
                        "Feed answered HTTP 503", "/ingestion"));

        String body = NotificationMailer.body(waiting, "zh", "https://careeros.example/");

        assertThat(NotificationMailer.subject(waiting.size(), "zh"))
                .isEqualTo("Career OS：收件箱里有 3 条待看的信号");
        assertThat(body).contains(
                "收件箱里等你处理的信号：",
                "- Acme 的 Senior Analyst —— 你设置的提醒已经到期",
                "- Globex 的 Data Analyst —— 14 天以上没有动静",
                "- Hiring board —— 昨晚的抓取失败了",
                "  Feed answered HTTP 503",
                "  https://careeros.example/ingestion",
                "同一条信号最多寄一次。");
    }

    @Test
    void the_transport_receives_the_rendered_letter_for_the_account() {
        EmailSender email = mock(EmailSender.class);

        new NotificationMailer(email, "https://careeros.example").send(
                "alice@example.com", List.of(reminder()), "zh");

        verify(email).send("alice@example.com", "Career OS：收件箱里有 1 条待看的信号",
                "收件箱里等你处理的信号：\n\n"
                        + "- Acme 的 Senior Analyst —— 你设置的提醒已经到期\n"
                        + "  https://careeros.example/applications?application=app-1\n\n"
                        + "在应用里读过或处理之后，这条信号就会安静下来；同一条信号最多寄一次。\n");
    }
}
