package com.careeros.notification.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.application.repository.ApplicationRepository;
import com.careeros.auth.entity.User;
import com.careeros.auth.repository.UserRepository;
import com.careeros.job.repository.IngestionFeedRepository;
import com.careeros.job.repository.SavedSearchRepository;
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
 * The morning sweep that carries the inbox out of the app (roadmap 22.1).
 *
 * <p>What is pinned: the audience is the union of the three kinds of account, so an account in
 * more than one half gets one letter (and an account with only a saved search is asked at all);
 * an account with nothing waiting gets no letter at all; the latch is written only after the
 * transport accepts, so a refusal is retried tomorrow rather than recorded as delivered; one
 * account's bad state does not cost the others their morning; and a finished pass moves the
 * heartbeat while a pass that could not read its audience does not.
 */
class NotificationMailServiceTest {

    private static final UUID ALICE = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final UUID BOB = UUID.fromString("22222222-2222-4222-8222-222222222222");
    private static final UUID CAROL = UUID.fromString("33333333-3333-4333-8333-333333333333");

    private NotificationService notifications;
    private NotificationMailer mailer;
    private ApplicationRepository applications;
    private IngestionFeedRepository feeds;
    private SavedSearchRepository savedSearches;
    private UserRepository users;
    private NotificationDeliveryMetrics metrics;
    private MailPreferenceService preferences;
    private NotificationMailService service;

    @BeforeEach
    void setUp() {
        notifications = mock(NotificationService.class);
        mailer = mock(NotificationMailer.class);
        applications = mock(ApplicationRepository.class);
        feeds = mock(IngestionFeedRepository.class);
        savedSearches = mock(SavedSearchRepository.class);
        users = mock(UserRepository.class);
        metrics = mock(NotificationDeliveryMetrics.class);
        preferences = mock(MailPreferenceService.class);
        service = new NotificationMailService(notifications, mailer, applications, feeds,
                savedSearches, users, metrics, preferences);
        when(applications.distinctUserIds()).thenReturn(List.of());
        when(feeds.distinctUserIds()).thenReturn(List.of());
        when(savedSearches.distinctUserIds()).thenReturn(List.of());
        when(preferences.optedOut(MailList.SIGNALS)).thenReturn(Set.of());
    }

    private static NotificationItem item(String key) {
        return new NotificationItem(key, NotificationService.KIND_STALE, "Role", "Acme", "applied",
                null, null, "/applications?application=" + key, OffsetDateTime.now(), false);
    }

    private static User account(UUID id, String email, String locale) {
        User user = new User();
        user.setId(id);
        user.setEmail(email);
        user.setLocale(locale);
        return user;
    }

    @Test
    void each_account_is_asked_once_even_when_it_is_in_every_half_of_the_audience() {
        when(applications.distinctUserIds()).thenReturn(List.of(ALICE));
        when(feeds.distinctUserIds()).thenReturn(List.of(ALICE, BOB));
        when(savedSearches.distinctUserIds()).thenReturn(List.of(ALICE, BOB));
        when(notifications.awaitingDelivery(any())).thenReturn(List.of());

        assertThat(service.mailPending()).isZero();

        verify(notifications).awaitingDelivery(ALICE);
        verify(notifications).awaitingDelivery(BOB);
        verify(mailer, never()).send(any(), anyString(), any(), any());
        verify(metrics).recordSweep(any());
        verify(metrics, never()).recordSent(any());
    }

    /**
     * The audience used to be applications ∪ feeds, so a reader who only browses with saved
     * questions was never asked -- the search's news had no way out of the app for them.
     */
    @Test
    void an_account_that_only_keeps_a_saved_search_still_gets_its_morning() {
        when(savedSearches.distinctUserIds()).thenReturn(List.of(CAROL));
        when(notifications.awaitingDelivery(CAROL)).thenReturn(List.of(item("s")));
        when(users.findById(CAROL))
                .thenReturn(Optional.of(account(CAROL, "carol@example.com", "en")));

        assertThat(service.mailPending()).isEqualTo(1);

        verify(mailer).send(eq(CAROL), eq("carol@example.com"), any(), anyString());
        verify(notifications).markNotified(eq(CAROL), eq(List.of("s")), any());
    }

    @Test
    void an_accepted_letter_is_latched_for_every_item_it_carried() {
        when(applications.distinctUserIds()).thenReturn(List.of(ALICE));
        List<NotificationItem> waiting = List.of(item("a"), item("b"));
        when(notifications.awaitingDelivery(ALICE)).thenReturn(waiting);
        when(users.findById(ALICE)).thenReturn(Optional.of(account(ALICE, "alice@example.com", "zh")));

        assertThat(service.mailPending()).isEqualTo(1);

        verify(mailer).send(ALICE, "alice@example.com", waiting, "zh");
        verify(notifications).markNotified(eq(ALICE), eq(List.of("a", "b")), any());
        verify(metrics).recordSent(any());
    }

    @Test
    void a_refused_letter_is_not_latched_and_the_other_accounts_are_still_mailed() {
        when(applications.distinctUserIds()).thenReturn(List.of(ALICE, BOB));
        when(notifications.awaitingDelivery(ALICE)).thenReturn(List.of(item("a")));
        when(notifications.awaitingDelivery(BOB)).thenReturn(List.of(item("b")));
        when(users.findById(ALICE)).thenReturn(Optional.of(account(ALICE, "alice@example.com", "en")));
        when(users.findById(BOB)).thenReturn(Optional.of(account(BOB, "bob@example.com", "en")));
        doThrow(new MailSendException("relay said 550")).when(mailer)
                .send(eq(ALICE), eq("alice@example.com"), any(), anyString());

        assertThat(service.mailPending()).isEqualTo(1);

        verify(mailer).send(eq(BOB), eq("bob@example.com"), any(), anyString());
        verify(notifications, never()).markNotified(eq(ALICE), any(), any());
        verify(notifications).markNotified(eq(BOB), any(), any());
        verify(metrics).recordRefused();
        verify(metrics, times(1)).recordSent(any());
    }

    @Test
    void an_account_with_no_row_or_no_address_is_skipped_without_a_letter_or_a_latch() {
        when(applications.distinctUserIds()).thenReturn(List.of(ALICE, BOB, CAROL));
        when(notifications.awaitingDelivery(any())).thenReturn(List.of(item("a")));
        when(users.findById(ALICE)).thenReturn(Optional.empty());
        when(users.findById(BOB)).thenReturn(Optional.of(account(BOB, "", "en")));
        when(users.findById(CAROL)).thenReturn(Optional.of(account(CAROL, "carol@example.com", "en")));

        assertThat(service.mailPending()).isEqualTo(1);

        verify(mailer, times(1)).send(eq(CAROL), eq("carol@example.com"), any(), anyString());
        verify(notifications, never()).markNotified(eq(ALICE), any(), any());
        verify(notifications, never()).markNotified(eq(BOB), any(), any());
        verify(notifications).markNotified(eq(CAROL), any(), any());
        verify(metrics, never()).recordRefused();
        verify(metrics, times(1)).recordSent(any());
    }

    @Test
    void one_account_that_cannot_even_be_read_does_not_cost_the_others_their_morning() {
        when(applications.distinctUserIds()).thenReturn(List.of(ALICE, BOB));
        when(notifications.awaitingDelivery(ALICE)).thenThrow(new IllegalStateException("bad row"));
        when(notifications.awaitingDelivery(BOB)).thenReturn(List.of(item("b")));
        when(users.findById(BOB)).thenReturn(Optional.of(account(BOB, "bob@example.com", "en")));

        assertThat(service.mailPending()).isEqualTo(1);

        verify(mailer).send(eq(BOB), eq("bob@example.com"), any(), anyString());
    }

    @Test
    void an_account_that_turned_the_letter_off_is_not_even_asked_what_is_waiting() {
        when(applications.distinctUserIds()).thenReturn(List.of(ALICE, BOB));
        when(preferences.optedOut(MailList.SIGNALS)).thenReturn(Set.of(ALICE));
        when(notifications.awaitingDelivery(BOB)).thenReturn(List.of(item("b")));
        when(users.findById(BOB)).thenReturn(Optional.of(account(BOB, "bob@example.com", "en")));

        assertThat(service.mailPending()).isEqualTo(1);

        verify(notifications, never()).awaitingDelivery(ALICE);
        verify(mailer, times(1)).send(eq(BOB), eq("bob@example.com"), any(), anyString());
        verify(notifications, never()).markNotified(eq(ALICE), any(), any());
        verify(metrics).recordSweep(any());
    }

    @Test
    void a_sweep_that_cannot_read_its_audience_writes_no_heartbeat() {
        when(applications.distinctUserIds()).thenThrow(new IllegalStateException("db down"));

        assertThatThrownBy(() -> service.mailPending()).isInstanceOf(IllegalStateException.class);

        verify(metrics, never()).recordSweep(any());
    }
}
