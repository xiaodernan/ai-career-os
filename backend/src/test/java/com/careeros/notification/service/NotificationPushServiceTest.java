package com.careeros.notification.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.application.repository.ApplicationRepository;
import com.careeros.notification.dto.NotificationDtos.NotificationItem;
import com.careeros.push.entity.PushSubscription;
import com.careeros.push.repository.PushSubscriptionRepository;
import com.careeros.push.service.PushDeliveryMetrics;
import com.careeros.push.service.PushSender;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/**
 * The morning sweep that rings the reader's browsers (roadmap 33.3).
 *
 * <p>What is pinned: one waiting morning is one ring per browser, and an account with nothing
 * waiting costs no outbound call at all; the episode's latch is written only when some browser
 * accepted, so a morning that every registration refused is tried again rather than remembered
 * as rung; one browser accepting is enough to latch, because the ring reached the reader and a
 * second morning must not ring the same signal again; a registration the push service retired is
 * deleted, since it would answer `gone` every morning; and one account in a bad state does not
 * cost the others their ring.
 *
 * <p>The minute clock (roadmap 35.1) is pinned as a pass over a window: only the accounts the
 * board names for that window are rung, an episode the morning already carried is not asked
 * again because the latch is the morning's, and a broken account cannot silence the rest of the
 * tick.
 */
class NotificationPushServiceTest {

    private static final UUID ALICE = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final UUID BOB = UUID.fromString("22222222-2222-4222-8222-222222222222");
    private static final UUID CAROL = UUID.fromString("33333333-3333-4333-8333-333333333333");

    private static final OffsetDateTime SINCE = OffsetDateTime.parse("2026-10-30T10:00:00Z");
    private static final OffsetDateTime UNTIL = OffsetDateTime.parse("2026-10-30T10:01:00Z");

    private NotificationService notifications;
    private PushSender sender;
    private PushSubscriptionRepository subscriptions;
    private PushDeliveryMetrics metrics;
    private ApplicationRepository applications;
    private NotificationPushService service;

    @BeforeEach
    void setUp() {
        notifications = mock(NotificationService.class);
        sender = mock(PushSender.class);
        subscriptions = mock(PushSubscriptionRepository.class);
        metrics = mock(PushDeliveryMetrics.class);
        applications = mock(ApplicationRepository.class);
        service = new NotificationPushService(notifications, sender, subscriptions, metrics,
                applications);
        when(subscriptions.distinctUserIds()).thenReturn(List.of());
        when(applications.findUserIdsWithReminderBetween(any(), any())).thenReturn(List.of());
    }

    private static NotificationItem item(String key) {
        return new NotificationItem(key, NotificationService.KIND_STALE, "Role", "Acme", "applied",
                null, null, "/applications?application=" + key, OffsetDateTime.now(), false);
    }

    private static PushSubscription browser() {
        return mock(PushSubscription.class);
    }

    private static void accepts(PushSender sender, PushSubscription browser) {
        when(sender.send(browser)).thenReturn(PushSender.Outcome.SENT);
    }

    @Test
    void one_waiting_morning_rings_every_browser_and_latches_the_episode_once() {
        PushSubscription laptop = browser();
        PushSubscription phone = browser();
        accepts(sender, laptop);
        accepts(sender, phone);
        when(subscriptions.distinctUserIds()).thenReturn(List.of(ALICE));
        when(subscriptions.findByUserIdOrderByCreatedAtDesc(ALICE))
                .thenReturn(List.of(laptop, phone));
        when(notifications.awaitingPush(ALICE)).thenReturn(List.of(item("a"), item("b")));

        assertThat(service.pushPending()).isEqualTo(1);

        verify(sender, times(1)).send(laptop);
        verify(sender, times(1)).send(phone);
        verify(metrics, times(2)).record(PushSender.Outcome.SENT);
        verify(notifications).markPushed(eq(ALICE), eq(List.of("a", "b")), any());
        verify(subscriptions, never()).deleteAll(anyList());
    }

    @Test
    void an_account_with_nothing_waiting_costs_no_outbound_call() {
        when(subscriptions.distinctUserIds()).thenReturn(List.of(ALICE));
        when(notifications.awaitingPush(ALICE)).thenReturn(List.of());

        assertThat(service.pushPending()).isZero();

        verify(sender, never()).send(any());
        verify(notifications, never()).markPushed(any(), anyList(), any());
    }

    @Test
    void a_retired_registration_is_deleted_and_a_morning_that_rang_nothing_is_not_latched() {
        PushSubscription dead = browser();
        PushSubscription refused = browser();
        when(sender.send(dead)).thenReturn(PushSender.Outcome.GONE);
        when(sender.send(refused)).thenReturn(PushSender.Outcome.REFUSED);
        when(subscriptions.distinctUserIds()).thenReturn(List.of(ALICE));
        when(subscriptions.findByUserIdOrderByCreatedAtDesc(ALICE))
                .thenReturn(List.of(dead, refused));
        when(notifications.awaitingPush(ALICE)).thenReturn(List.of(item("a")));

        assertThat(service.pushPending()).isZero();

        verify(subscriptions).deleteAll(List.of(dead));
        verify(metrics).record(PushSender.Outcome.GONE);
        verify(metrics).record(PushSender.Outcome.REFUSED);
        verify(notifications, never()).markPushed(any(), anyList(), any());
    }

    @Test
    void one_browser_accepting_is_enough_to_latch_the_episode() {
        PushSubscription refused = browser();
        PushSubscription accepted = browser();
        when(sender.send(refused)).thenReturn(PushSender.Outcome.REFUSED);
        accepts(sender, accepted);
        when(subscriptions.distinctUserIds()).thenReturn(List.of(ALICE));
        when(subscriptions.findByUserIdOrderByCreatedAtDesc(ALICE))
                .thenReturn(List.of(refused, accepted));
        when(notifications.awaitingPush(ALICE)).thenReturn(List.of(item("a")));

        assertThat(service.pushPending()).isEqualTo(1);

        verify(notifications).markPushed(eq(ALICE), eq(List.of("a")), any());
    }

    @Test
    void a_morning_that_every_registration_refused_is_asked_again_the_next_morning() {
        PushSubscription refused = browser();
        when(sender.send(refused)).thenReturn(PushSender.Outcome.REFUSED);
        when(subscriptions.distinctUserIds()).thenReturn(List.of(ALICE));
        when(subscriptions.findByUserIdOrderByCreatedAtDesc(ALICE)).thenReturn(List.of(refused));
        when(notifications.awaitingPush(ALICE)).thenReturn(List.of(item("a")));

        assertThat(service.pushPending()).isZero();
        assertThat(service.pushPending()).isZero();

        verify(sender, times(2)).send(refused);
        verify(notifications, never()).markPushed(any(), anyList(), any());
    }

    @Test
    void a_deployment_without_keys_runs_the_audience_without_latching_a_ring() {
        PushSubscription browser = browser();
        when(sender.send(browser)).thenReturn(PushSender.Outcome.NOT_CONFIGURED);
        when(subscriptions.distinctUserIds()).thenReturn(List.of(ALICE));
        when(subscriptions.findByUserIdOrderByCreatedAtDesc(ALICE)).thenReturn(List.of(browser));
        when(notifications.awaitingPush(ALICE)).thenReturn(List.of(item("a")));

        assertThat(service.pushPending()).isZero();

        verify(metrics).record(PushSender.Outcome.NOT_CONFIGURED);
        verify(notifications, never()).markPushed(any(), anyList(), any());
    }

    @Test
    void an_account_whose_registration_vanished_is_skipped_without_a_call() {
        when(subscriptions.distinctUserIds()).thenReturn(List.of(CAROL));
        when(subscriptions.findByUserIdOrderByCreatedAtDesc(CAROL)).thenReturn(List.of());
        when(notifications.awaitingPush(CAROL)).thenReturn(List.of(item("c")));

        assertThat(service.pushPending()).isZero();

        verify(sender, never()).send(any());
        verify(notifications, never()).markPushed(any(), anyList(), any());
    }

    @Test
    void one_account_that_cannot_even_be_read_does_not_cost_the_others_their_ring() {
        PushSubscription bob = browser();
        accepts(sender, bob);
        when(subscriptions.distinctUserIds()).thenReturn(List.of(ALICE, BOB));
        when(notifications.awaitingPush(ALICE)).thenThrow(new IllegalStateException("bad row"));
        when(notifications.awaitingPush(BOB)).thenReturn(List.of(item("b")));
        when(subscriptions.findByUserIdOrderByCreatedAtDesc(BOB)).thenReturn(List.of(bob));

        assertThat(service.pushPending()).isEqualTo(1);

        verify(notifications).markPushed(eq(BOB), eq(List.of("b")), any());
    }

    @Test
    void a_tick_rings_only_the_accounts_the_board_named_for_its_window() {
        PushSubscription alicePhone = browser();
        accepts(sender, alicePhone);
        when(applications.findUserIdsWithReminderBetween(SINCE, UNTIL))
                .thenReturn(List.of(ALICE));
        when(subscriptions.findByUserIdOrderByCreatedAtDesc(ALICE))
                .thenReturn(List.of(alicePhone));
        when(notifications.awaitingPush(ALICE)).thenReturn(List.of(item("reminder:a:1")));

        assertThat(service.pushDue(SINCE, UNTIL)).isEqualTo(1);

        verify(applications).findUserIdsWithReminderBetween(SINCE, UNTIL);
        verify(sender).send(alicePhone);
        verify(notifications).markPushed(eq(ALICE), eq(List.of("reminder:a:1")), any());
        verify(subscriptions, never()).distinctUserIds();
    }

    @Test
    void a_window_with_nobody_due_rings_nobody_and_asks_no_browser_list() {
        assertThat(service.pushDue(SINCE, UNTIL)).isZero();

        verify(sender, never()).send(any());
        verify(subscriptions, never()).findByUserIdOrderByCreatedAtDesc(any());
        verify(notifications, never()).markPushed(any(), anyList(), any());
    }

    @Test
    void a_reminder_the_morning_already_rang_is_not_rung_again_by_the_tick() {
        when(applications.findUserIdsWithReminderBetween(SINCE, UNTIL))
                .thenReturn(List.of(ALICE));
        when(notifications.awaitingPush(ALICE)).thenReturn(List.of());

        assertThat(service.pushDue(SINCE, UNTIL)).isZero();

        verify(sender, never()).send(any());
        verify(notifications, never()).markPushed(any(), anyList(), any());
    }

    @Test
    void one_account_that_cannot_be_prepared_does_not_stop_the_tick_for_the_next() {
        PushSubscription bobPhone = browser();
        accepts(sender, bobPhone);
        when(applications.findUserIdsWithReminderBetween(SINCE, UNTIL))
                .thenReturn(List.of(ALICE, BOB));
        when(notifications.awaitingPush(ALICE)).thenThrow(new IllegalStateException("bad row"));
        when(notifications.awaitingPush(BOB)).thenReturn(List.of(item("reminder:b:2")));
        when(subscriptions.findByUserIdOrderByCreatedAtDesc(BOB))
                .thenReturn(List.of(bobPhone));

        assertThat(service.pushDue(SINCE, UNTIL)).isEqualTo(1);

        verify(notifications).markPushed(eq(BOB), eq(List.of("reminder:b:2")), any());
    }

    @Test
    void a_browser_that_refused_is_not_latched_so_the_next_morning_tries_again() {
        PushSubscription refused = browser();
        when(sender.send(refused)).thenReturn(PushSender.Outcome.REFUSED);
        when(applications.findUserIdsWithReminderBetween(SINCE, UNTIL))
                .thenReturn(List.of(ALICE));
        when(subscriptions.findByUserIdOrderByCreatedAtDesc(ALICE))
                .thenReturn(List.of(refused));
        when(notifications.awaitingPush(ALICE)).thenReturn(List.of(item("reminder:a:1")));

        assertThat(service.pushDue(SINCE, UNTIL)).isZero();

        verify(metrics).record(PushSender.Outcome.REFUSED);
        verify(notifications, never()).markPushed(any(), anyList(), any());
    }
}
