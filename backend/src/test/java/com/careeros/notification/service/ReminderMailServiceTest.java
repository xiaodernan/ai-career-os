package com.careeros.notification.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.application.repository.ApplicationRepository;
import com.careeros.auth.entity.User;
import com.careeros.auth.repository.UserRepository;
import com.careeros.mail.service.MailList;
import com.careeros.mail.service.MailPreferenceService;
import com.careeros.notification.dto.NotificationDtos.NotificationItem;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.mail.MailSendException;

/**
 * The minute clock's letter (roadmap 41.1).
 *
 * <p>What is pinned: only the reminder that fell inside the tick's window is mailed -- the
 * morning's other items wait -- and the letter carries that episode's own key to the latch, so
 * the morning sweep cannot send it a second time. A reader who turned the dial off is not asked
 * what is waiting at all, and a reminder whose item the app no longer shows (read or dismissed)
 * is not mailed. A refusal is a warn line and no latch, so the morning letter remains the
 * fallback rather than the episode being remembered as delivered.
 */
class ReminderMailServiceTest {

    private static final UUID ALICE = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final UUID BOB = UUID.fromString("22222222-2222-4222-8222-222222222222");
    private static final OffsetDateTime SINCE = OffsetDateTime.parse("2026-10-30T14:00:00Z");
    private static final OffsetDateTime UNTIL = OffsetDateTime.parse("2026-10-30T14:01:00Z");

    private NotificationService notifications;
    private ReminderMailer mailer;
    private ApplicationRepository applications;
    private UserRepository users;
    private NotificationDeliveryMetrics metrics;
    private MailPreferenceService preferences;
    private ReminderMailService service;

    @BeforeEach
    void setUp() {
        notifications = mock(NotificationService.class);
        mailer = mock(ReminderMailer.class);
        applications = mock(ApplicationRepository.class);
        users = mock(UserRepository.class);
        metrics = mock(NotificationDeliveryMetrics.class);
        preferences = mock(MailPreferenceService.class);
        service = new ReminderMailService(notifications, mailer, applications, users, metrics,
                preferences);
        when(applications.findUserIdsWithReminderBetween(SINCE, UNTIL)).thenReturn(List.of());
        when(preferences.optedOut(MailList.REMINDERS)).thenReturn(Set.of());
    }

    private static NotificationItem reminder(String title, String company, OffsetDateTime at) {
        return new NotificationItem("reminder:" + at.toInstant().getEpochSecond(),
                NotificationService.KIND_REMINDER, title, company, "applied", null, null,
                "/applications?application=a", at, false);
    }

    private static NotificationItem stale() {
        return new NotificationItem("stale:a:1", NotificationService.KIND_STALE, "Old role",
                "Acme", "applied", null, null, "/applications?application=a",
                OffsetDateTime.parse("2026-10-20T00:00:00Z"), false);
    }

    private static User account(UUID id, String email, String locale) {
        User user = new User();
        user.setId(id);
        user.setEmail(email);
        user.setLocale(locale);
        return user;
    }

    @Test
    void a_reminder_due_in_the_window_is_mailed_and_latched_on_its_own_episode() {
        NotificationItem due = reminder("Senior Analyst", "Acme", SINCE.plusSeconds(30));
        when(applications.findUserIdsWithReminderBetween(SINCE, UNTIL)).thenReturn(List.of(ALICE));
        when(notifications.awaitingDelivery(ALICE)).thenReturn(List.of(due, stale()));
        when(users.findById(ALICE))
                .thenReturn(Optional.of(account(ALICE, "alice@example.com", "zh")));

        assertThat(service.mailDue(SINCE, UNTIL)).isEqualTo(1);

        verify(mailer).send(eq(ALICE), eq("alice@example.com"), eq(List.of(due)), eq("zh"));
        verify(notifications).markNotified(eq(ALICE), eq(List.of(due.key())), any());
        verify(metrics).recordSent(any());
    }

    /**
     * The latch is what the morning sweep reads, so an episode already mailed at its moment is
     * not carried again by the next morning's letter.
     */
    @Test
    void an_episode_the_morning_already_mailed_is_not_mailed_again() {
        when(applications.findUserIdsWithReminderBetween(SINCE, UNTIL)).thenReturn(List.of(ALICE));
        when(notifications.awaitingDelivery(ALICE)).thenReturn(List.of(stale()));

        assertThat(service.mailDue(SINCE, UNTIL)).isZero();

        verify(mailer, never()).send(any(), anyString(), any(), anyString());
        verify(notifications, never()).markNotified(any(), any(), any());
        verify(metrics, never()).recordSent(any());
    }

    @Test
    void an_account_that_turned_the_reminder_letter_off_is_not_even_asked() {
        when(applications.findUserIdsWithReminderBetween(SINCE, UNTIL))
                .thenReturn(List.of(ALICE, BOB));
        when(preferences.optedOut(MailList.REMINDERS)).thenReturn(Set.of(ALICE));
        NotificationItem due = reminder("Senior Analyst", "Acme", UNTIL);
        when(notifications.awaitingDelivery(BOB)).thenReturn(List.of(due));
        when(users.findById(BOB)).thenReturn(Optional.of(account(BOB, "bob@example.com", "en")));

        assertThat(service.mailDue(SINCE, UNTIL)).isEqualTo(1);

        verify(notifications, never()).awaitingDelivery(ALICE);
        verify(mailer, never()).send(eq(ALICE), anyString(), any(), anyString());
        verify(notifications).markNotified(eq(BOB), any(), any());
    }

    @Test
    void a_refused_letter_is_not_latched_so_the_morning_still_carries_it() {
        NotificationItem due = reminder("Senior Analyst", "Acme", UNTIL);
        when(applications.findUserIdsWithReminderBetween(SINCE, UNTIL)).thenReturn(List.of(ALICE));
        when(notifications.awaitingDelivery(ALICE)).thenReturn(List.of(due));
        when(users.findById(ALICE))
                .thenReturn(Optional.of(account(ALICE, "alice@example.com", "en")));
        doThrow(new MailSendException("relay said 550")).when(mailer)
                .send(eq(ALICE), eq("alice@example.com"), any(), anyString());

        assertThat(service.mailDue(SINCE, UNTIL)).isZero();

        verify(notifications, never()).markNotified(eq(ALICE), any(), any());
        verify(metrics).recordRefused();
        verify(metrics, never()).recordSent(any());
    }

    @Test
    void an_account_with_no_row_or_address_is_skipped_without_a_letter_or_a_latch() {
        NotificationItem due = reminder("Senior Analyst", "Acme", UNTIL);
        when(applications.findUserIdsWithReminderBetween(SINCE, UNTIL))
                .thenReturn(List.of(ALICE, BOB));
        when(notifications.awaitingDelivery(any())).thenReturn(List.of(due));
        when(users.findById(ALICE)).thenReturn(Optional.empty());
        when(users.findById(BOB)).thenReturn(Optional.of(account(BOB, "", "en")));

        assertThat(service.mailDue(SINCE, UNTIL)).isZero();

        verify(mailer, never()).send(any(), anyString(), any(), anyString());
        verify(notifications, never()).markNotified(any(), any(), any());
        verify(metrics, never()).recordSent(any());
    }

    @Test
    void a_reminder_outside_the_window_is_not_this_ticks_news() {
        when(applications.findUserIdsWithReminderBetween(SINCE, UNTIL)).thenReturn(List.of(ALICE));
        when(notifications.awaitingDelivery(ALICE))
                .thenReturn(List.of(reminder("Older", "Acme", SINCE.minusMinutes(5))));

        assertThat(service.mailDue(SINCE, UNTIL)).isZero();

        verify(mailer, never()).send(any(), anyString(), any(), anyString());
    }

    @Test
    void one_account_that_cannot_be_read_does_not_cost_the_others_their_letter() {
        NotificationItem due = reminder("Senior Analyst", "Acme", UNTIL);
        when(applications.findUserIdsWithReminderBetween(SINCE, UNTIL))
                .thenReturn(List.of(ALICE, BOB));
        when(notifications.awaitingDelivery(ALICE)).thenThrow(new IllegalStateException("bad row"));
        when(notifications.awaitingDelivery(BOB)).thenReturn(List.of(due));
        when(users.findById(BOB)).thenReturn(Optional.of(account(BOB, "bob@example.com", "en")));

        assertThat(service.mailDue(SINCE, UNTIL)).isEqualTo(1);

        verify(mailer).send(eq(BOB), eq("bob@example.com"), any(), anyString());
    }
}
