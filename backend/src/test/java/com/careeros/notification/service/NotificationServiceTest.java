package com.careeros.notification.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.careeros.inbound.entity.InboundMail;
import com.careeros.inbound.repository.InboundMailRepository;
import com.careeros.job.entity.IngestionFeed;
import com.careeros.job.entity.IngestionRun;
import com.careeros.job.repository.IngestionFeedRepository;
import com.careeros.job.repository.IngestionRunRepository;
import com.careeros.job.service.SavedSearchMatcher;
import com.careeros.notification.dto.NotificationDtos.Inbox;
import com.careeros.notification.dto.NotificationDtos.NotificationItem;
import com.careeros.notification.entity.NotificationState;
import com.careeros.notification.repository.NotificationStateRepository;
import com.careeros.report.dto.DashboardDtos.AttentionItem;
import com.careeros.report.repository.DashboardRepository;
import java.time.OffsetDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.Pageable;

/**
 * The inbox's synthesis and its state (roadmap 19.3).
 *
 * <p>Three things are worth pinning here. Nothing is stored per notification: the same signals
 * have to become the same items on every read, and a dismissed item has to stay dismissed
 * without a row describing it. The key has to name the episode, so a new reminder or a new
 * update raises a new item instead of inheriting the old dismissal. And a write only touches
 * what the inbox is showing -- a stale browser tab cannot file state for a signal that ended.
 */
class NotificationServiceTest {

    private static final UUID ALICE = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final UUID APP = UUID.fromString("22222222-2222-4222-8222-222222222222");
    private static final UUID FEED = UUID.fromString("33333333-3333-4333-8333-333333333333");
    private static final UUID RUN = UUID.fromString("44444444-4444-4444-8444-444444444444");
    private static final UUID RUN2 = UUID.fromString("55555555-5555-4555-8555-555555555555");
    private static final UUID SEARCH = UUID.fromString("66666666-6666-4666-8666-666666666666");
    private static final UUID MAIL = UUID.fromString("77777777-7777-4777-8777-777777777777");

    private DashboardRepository dashboard;
    private IngestionRunRepository runs;
    private IngestionFeedRepository feeds;
    private SavedSearchMatcher savedSearches;
    private NotificationStateRepository states;
    private InboundMailRepository inbound;
    private Map<String, NotificationState> store;
    private NotificationService service;

    @BeforeEach
    void setUp() {
        dashboard = mock(DashboardRepository.class);
        runs = mock(IngestionRunRepository.class);
        feeds = mock(IngestionFeedRepository.class);
        savedSearches = mock(SavedSearchMatcher.class);
        states = mock(NotificationStateRepository.class);
        inbound = mock(InboundMailRepository.class);
        store = new LinkedHashMap<>();

        when(states.findByUserId(ALICE)).thenAnswer(invocation -> List.copyOf(store.values()));
        when(states.findByUserIdAndSignalKey(eq(ALICE), anyString())).thenAnswer(invocation ->
                Optional.ofNullable(store.get(invocation.getArgument(1, String.class))));
        when(states.save(any(NotificationState.class))).thenAnswer(invocation -> {
            NotificationState state = invocation.getArgument(0);
            store.put(state.getSignalKey(), state);
            return state;
        });
        when(feeds.findByUserIdOrderByCreatedAtDesc(ALICE)).thenReturn(List.of());
        when(runs.findByUserIdOrderByStartedAtDescIdDesc(eq(ALICE), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of()));
        when(savedSearches.alerts(eq(ALICE), any())).thenReturn(List.of());
        when(inbound.findByUserIdAndApplicationIdIsNotNullOrderByReceivedAtDescIdDesc(
                eq(ALICE), any(Pageable.class))).thenReturn(List.of());

        service = new NotificationService(dashboard, runs, feeds, savedSearches, states, inbound);
    }

    private static AttentionItem attention(String reason, OffsetDateTime reminderAt,
                                           OffsetDateTime updatedAt) {
        return new AttentionItem(APP, "Senior Analyst", "Acme", "applied", reason,
                reminderAt, updatedAt);
    }

    private static IngestionFeed named(String name) {
        IngestionFeed feed = mock(IngestionFeed.class);
        when(feed.getId()).thenReturn(FEED);
        when(feed.getName()).thenReturn(name);
        return feed;
    }

    private static IngestionRun run(UUID id, String status, String error,
                                    Map<String, Object> counts, OffsetDateTime startedAt) {
        IngestionRun run = mock(IngestionRun.class);
        when(run.getId()).thenReturn(id);
        when(run.getFeedId()).thenReturn(FEED);
        when(run.getStatus()).thenReturn(status);
        when(run.getError()).thenReturn(error);
        when(run.getCounts()).thenReturn(counts);
        when(run.getStartedAt()).thenReturn(startedAt);
        return run;
    }

    private void withAttention(AttentionItem... items) {
        when(dashboard.attention(ALICE, NotificationService.STALE_DAYS,
                NotificationService.ATTENTION_LIMIT)).thenReturn(List.of(items));
    }

    private void withRuns(IngestionRun... items) {
        // Built before the stubbing call: a mock created inside another `when(...)` argument
        // reads as unfinished stubbing to Mockito.
        IngestionFeed feed = named("Hiring board");
        when(feeds.findByUserIdOrderByCreatedAtDesc(ALICE)).thenReturn(List.of(feed));
        when(runs.findByUserIdOrderByStartedAtDescIdDesc(eq(ALICE), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(items)));
    }

    @Test
    void a_due_reminder_and_a_quiet_application_become_two_unread_items() {
        OffsetDateTime now = OffsetDateTime.now();
        OffsetDateTime updated = now.minusDays(20);
        withAttention(attention("reminder_due", now.minusHours(1), now.minusDays(2)),
                attention("stale", null, updated));

        Inbox inbox = service.inbox(ALICE);

        assertThat(inbox.unread()).isEqualTo(2);
        assertThat(inbox.items()).extracting(NotificationItem::kind)
                .containsExactlyInAnyOrder(NotificationService.KIND_REMINDER,
                        NotificationService.KIND_STALE);
        NotificationItem reminder = inbox.items().stream()
                .filter(item -> NotificationService.KIND_REMINDER.equals(item.kind()))
                .findFirst().orElseThrow();
        assertThat(reminder.title()).isEqualTo("Senior Analyst");
        assertThat(reminder.subject()).isEqualTo("Acme");
        assertThat(reminder.status()).isEqualTo("applied");
        assertThat(reminder.link()).isEqualTo("/applications?application=" + APP);
        assertThat(reminder.read()).isFalse();
        assertThat(reminder.key()).contains(APP.toString());
        NotificationItem stale = inbox.items().stream()
                .filter(item -> NotificationService.KIND_STALE.equals(item.kind()))
                .findFirst().orElseThrow();
        assertThat(stale.at()).isEqualTo(updated.plusDays(NotificationService.STALE_DAYS));
    }

    @Test
    void items_are_ordered_by_when_they_happened_whichever_source_they_came_from() {
        OffsetDateTime now = OffsetDateTime.now();
        withAttention(attention("stale", null, now.minusDays(30)));
        withRuns(run(RUN, IngestionRun.STATUS_FAILED, "Feed answered HTTP 503", null,
                now.minusHours(2)));

        Inbox inbox = service.inbox(ALICE);

        assertThat(inbox.items()).extracting(NotificationItem::kind)
                .containsExactly(NotificationService.KIND_INGESTION_FAILED,
                        NotificationService.KIND_STALE);
    }

    @Test
    void a_failed_pull_is_an_item_and_a_quiet_completed_run_is_not() {
        OffsetDateTime now = OffsetDateTime.now();
        withRuns(
                run(RUN, IngestionRun.STATUS_COMPLETED, null, Map.of("create", 0), now.minusHours(1)),
                run(UUID.randomUUID(), IngestionRun.STATUS_FAILED, "Feed answered HTTP 503", null,
                        now.minusHours(2)),
                run(UUID.randomUUID(), IngestionRun.STATUS_COMPLETED, null, Map.of("create", 3),
                        now.minusHours(3)));

        Inbox inbox = service.inbox(ALICE);

        assertThat(inbox.items()).hasSize(2);
        NotificationItem failed = inbox.items().stream()
                .filter(item -> NotificationService.KIND_INGESTION_FAILED.equals(item.kind()))
                .findFirst().orElseThrow();
        assertThat(failed.title()).isEqualTo("Hiring board");
        assertThat(failed.note()).isEqualTo("Feed answered HTTP 503");
        assertThat(failed.link()).isEqualTo("/ingestion");
        NotificationItem created = inbox.items().stream()
                .filter(item -> NotificationService.KIND_INGESTION_CREATED.equals(item.kind()))
                .findFirst().orElseThrow();
        assertThat(created.count()).isEqualTo(3);
    }

    @Test
    void a_pull_older_than_the_lookback_is_history_not_news() {
        withRuns(run(RUN, IngestionRun.STATUS_FAILED, "Feed answered HTTP 503", null,
                OffsetDateTime.now().minusDays(NotificationService.LOOKBACK_DAYS + 1)));

        assertThat(service.inbox(ALICE).items()).isEmpty();
    }

    @Test
    void a_reply_that_landed_on_a_card_is_an_item_named_by_its_employer() {
        OffsetDateTime now = OffsetDateTime.now();
        InboundMail letter = mock(InboundMail.class);
        when(letter.getId()).thenReturn(MAIL);
        when(letter.getCompany()).thenReturn("Acme");
        when(letter.getSubject()).thenReturn("Your interview");
        when(letter.getIntent()).thenReturn("interview");
        when(letter.getReceivedAt()).thenReturn(now.minusHours(3));
        when(inbound.findByUserIdAndApplicationIdIsNotNullOrderByReceivedAtDescIdDesc(
                eq(ALICE), any(Pageable.class))).thenReturn(List.of(letter));

        Inbox inbox = service.inbox(ALICE);

        assertThat(inbox.items()).hasSize(1);
        NotificationItem item = inbox.items().get(0);
        assertThat(item.kind()).isEqualTo(NotificationService.KIND_REPLY);
        assertThat(item.key()).isEqualTo("reply:" + MAIL);
        assertThat(item.title()).isEqualTo("Acme");
        assertThat(item.subject()).isEqualTo("Your interview");
        assertThat(item.status()).isEqualTo("interview");
        assertThat(item.link()).isEqualTo("/replies?mail=" + MAIL);
        assertThat(item.at()).isEqualTo(now.minusHours(3));
        assertThat(item.read()).isFalse();
    }

    @Test
    void a_reply_with_no_employer_read_is_named_by_its_sender() {
        OffsetDateTime now = OffsetDateTime.now();
        InboundMail letter = mock(InboundMail.class);
        when(letter.getId()).thenReturn(MAIL);
        when(letter.getFromAddress()).thenReturn("recruiter@example.com");
        when(letter.getSubject()).thenReturn("Re: your application");
        when(letter.getReceivedAt()).thenReturn(now.minusMinutes(5));
        when(inbound.findByUserIdAndApplicationIdIsNotNullOrderByReceivedAtDescIdDesc(
                eq(ALICE), any(Pageable.class))).thenReturn(List.of(letter));

        NotificationItem item = service.inbox(ALICE).items().get(0);

        assertThat(item.title()).isEqualTo("recruiter@example.com");
        assertThat(item.status()).isNull();
    }

    @Test
    void a_reply_older_than_the_lookback_is_history_not_news() {
        InboundMail letter = mock(InboundMail.class);
        when(letter.getReceivedAt()).thenReturn(
                OffsetDateTime.now().minusDays(NotificationService.LOOKBACK_DAYS + 1));
        when(inbound.findByUserIdAndApplicationIdIsNotNullOrderByReceivedAtDescIdDesc(
                eq(ALICE), any(Pageable.class))).thenReturn(List.of(letter));

        assertThat(service.inbox(ALICE).items()).isEmpty();
    }

    @Test
    void a_dismissed_item_stays_gone_and_a_read_one_reads_as_read() {
        OffsetDateTime now = OffsetDateTime.now();
        OffsetDateTime updated = now.minusDays(20);
        withAttention(attention("reminder_due", now.minusHours(1), now.minusDays(2)),
                attention("stale", null, updated));
        store.put("reminder:" + APP + ":" + now.minusHours(1).toInstant().getEpochSecond(),
                state("reminder:" + APP + ":" + now.minusHours(1).toInstant().getEpochSecond(),
                        null, now.minusDays(1)));
        store.put("stale:" + APP + ":" + updated.toInstant().getEpochSecond(),
                state("stale:" + APP + ":" + updated.toInstant().getEpochSecond(),
                        now.minusDays(1), null));

        Inbox inbox = service.inbox(ALICE);

        assertThat(inbox.items()).hasSize(1);
        assertThat(inbox.items().get(0).kind()).isEqualTo(NotificationService.KIND_STALE);
        assertThat(inbox.items().get(0).read()).isTrue();
        assertThat(inbox.unread()).isZero();
    }

    @Test
    void a_new_episode_of_the_same_application_is_unread_again() {
        OffsetDateTime old = OffsetDateTime.now().minusDays(30);
        OffsetDateTime fresh = OffsetDateTime.now().minusDays(20);
        store.put("stale:" + APP + ":" + old.toInstant().getEpochSecond(),
                state("stale:" + APP + ":" + old.toInstant().getEpochSecond(),
                        null, OffsetDateTime.now().minusDays(29)));
        withAttention(attention("stale", null, fresh));

        Inbox inbox = service.inbox(ALICE);

        assertThat(inbox.items()).hasSize(1);
        assertThat(inbox.items().get(0).key())
                .isEqualTo("stale:" + APP + ":" + fresh.toInstant().getEpochSecond());
        assertThat(inbox.items().get(0).read()).isFalse();
    }

    @Test
    void marking_read_only_touches_items_the_inbox_is_showing() {
        OffsetDateTime now = OffsetDateTime.now();
        withAttention(attention("reminder_due", now.minusHours(1), now.minusDays(2)));
        String key = service.inbox(ALICE).items().get(0).key();

        Inbox after = service.markRead(ALICE, List.of(key, "stale:" + APP + ":999"));

        assertThat(after.unread()).isZero();
        assertThat(store).containsKey(key);
        assertThat(store).doesNotContainKey("stale:" + APP + ":999");
        assertThat(store.get(key).getReadAt()).isNotNull();
    }

    @Test
    void marking_all_read_clears_the_unread_count() {
        OffsetDateTime now = OffsetDateTime.now();
        withAttention(attention("reminder_due", now.minusHours(1), now.minusDays(2)),
                attention("stale", null, now.minusDays(20)));

        Inbox after = service.markAllRead(ALICE);

        assertThat(after.unread()).isZero();
        assertThat(after.items()).hasSize(2).allMatch(NotificationItem::read);
        assertThat(store).hasSize(2);
    }

    @Test
    void dismissing_files_the_item_and_answers_the_fresh_inbox() {
        OffsetDateTime now = OffsetDateTime.now();
        withAttention(attention("stale", null, now.minusDays(20)));
        String key = service.inbox(ALICE).items().get(0).key();

        Inbox after = service.dismiss(ALICE, key);

        assertThat(after.items()).isEmpty();
        assertThat(store.get(key).getDismissedAt()).isNotNull();
    }

    @Test
    void dismissing_a_key_the_inbox_is_not_showing_files_nothing() {
        withAttention(attention("stale", null, OffsetDateTime.now().minusDays(20)));

        Inbox after = service.dismiss(ALICE, "ingestion:" + RUN);

        assertThat(after.items()).hasSize(1);
        assertThat(store).isEmpty();
    }

    @Test
    void the_morning_mail_carries_only_what_is_unread_undismissed_and_unmailed() {
        OffsetDateTime now = OffsetDateTime.now();
        OffsetDateTime due = now.minusHours(1);
        OffsetDateTime updated = now.minusDays(20);
        withAttention(attention("reminder_due", due, null), attention("stale", null, updated));
        withRuns(run(RUN, IngestionRun.STATUS_FAILED, "Feed answered HTTP 503", null,
                        now.minusHours(2)),
                run(RUN2, IngestionRun.STATUS_FAILED, "Feed answered HTTP 502", null,
                        now.minusHours(3)));
        String reminderKey = "reminder:" + APP + ":" + due.toInstant().getEpochSecond();
        String staleKey = "stale:" + APP + ":" + updated.toInstant().getEpochSecond();
        NotificationState alreadyMailed = state(reminderKey, null, null);
        alreadyMailed.setNotifiedAt(now.minusMinutes(30));
        store.put(reminderKey, alreadyMailed);
        store.put(staleKey, state(staleKey, now.minusMinutes(10), null));
        store.put("ingestion:" + RUN, state("ingestion:" + RUN, null, now.minusMinutes(5)));

        List<NotificationItem> waiting = service.awaitingDelivery(ALICE);

        assertThat(waiting).extracting(NotificationItem::kind)
                .containsExactly(NotificationService.KIND_INGESTION_FAILED);
        assertThat(waiting.get(0).note()).isEqualTo("Feed answered HTTP 502");
    }

    @Test
    void a_mailed_episode_is_not_mailed_twice_and_a_new_episode_is_unmailed_again() {
        OffsetDateTime now = OffsetDateTime.now();
        withAttention(attention("stale", null, now.minusDays(20)));
        List<NotificationItem> first = service.awaitingDelivery(ALICE);
        assertThat(first).hasSize(1);

        service.markNotified(ALICE, first.stream().map(NotificationItem::key).toList(), now);

        assertThat(service.awaitingDelivery(ALICE)).isEmpty();
        assertThat(service.inbox(ALICE).items()).hasSize(1);
        assertThat(service.inbox(ALICE).unread()).isEqualTo(1);

        withAttention(attention("stale", null, now.minusDays(19)));

        assertThat(service.awaitingDelivery(ALICE)).extracting(NotificationItem::key)
                .containsExactly("stale:" + APP + ":"
                        + now.minusDays(19).toInstant().getEpochSecond());
    }

    @Test
    void a_read_after_the_letter_was_composed_still_gets_its_latch() {
        OffsetDateTime now = OffsetDateTime.now();
        withAttention(attention("stale", null, now.minusDays(20)));
        String key = service.awaitingDelivery(ALICE).get(0).key();

        service.markRead(ALICE, List.of(key));
        service.markNotified(ALICE, List.of(key), now);

        assertThat(store.get(key).getReadAt()).isNotNull();
        assertThat(store.get(key).getNotifiedAt()).isEqualTo(now);
    }

    /**
     * The letter and the ring are different doors (roadmap 33.3): a reader who turned the mail
     * off still asked to be woken, so an episode the letter already carried may still be rung.
     */
    @Test
    void a_mailed_episode_that_is_still_unread_may_still_be_rung() {
        OffsetDateTime now = OffsetDateTime.now();
        OffsetDateTime updated = now.minusDays(20);
        withAttention(attention("stale", null, updated));
        String key = "stale:" + APP + ":" + updated.toInstant().getEpochSecond();
        NotificationState mailed = state(key, null, null);
        mailed.setNotifiedAt(now.minusMinutes(30));
        store.put(key, mailed);

        assertThat(service.awaitingDelivery(ALICE)).isEmpty();
        assertThat(service.awaitingPush(ALICE)).extracting(NotificationItem::key)
                .containsExactly(key);
    }

    @Test
    void the_ring_carries_only_what_is_unread_undismissed_and_unpushed() {
        OffsetDateTime now = OffsetDateTime.now();
        OffsetDateTime due = now.minusHours(1);
        OffsetDateTime updated = now.minusDays(20);
        withAttention(attention("reminder_due", due, null), attention("stale", null, updated));
        withRuns(run(RUN, IngestionRun.STATUS_FAILED, "Feed answered HTTP 503", null,
                        now.minusHours(2)),
                run(RUN2, IngestionRun.STATUS_FAILED, "Feed answered HTTP 502", null,
                        now.minusHours(3)));
        String reminderKey = "reminder:" + APP + ":" + due.toInstant().getEpochSecond();
        String staleKey = "stale:" + APP + ":" + updated.toInstant().getEpochSecond();
        store.put(reminderKey, state(reminderKey, now.minusMinutes(10), null));
        store.put(staleKey, state(staleKey, null, now.minusMinutes(5)));
        NotificationState rung = state("ingestion:" + RUN, null, null);
        rung.setPushedAt(now.minusHours(1));
        store.put("ingestion:" + RUN, rung);

        assertThat(service.awaitingPush(ALICE)).extracting(NotificationItem::kind)
                .containsExactly(NotificationService.KIND_INGESTION_FAILED);
        assertThat(service.awaitingPush(ALICE).get(0).key()).isEqualTo("ingestion:" + RUN2);
    }

    @Test
    void a_pushed_episode_is_not_rung_twice_and_a_new_episode_is_unpushed_again() {
        OffsetDateTime now = OffsetDateTime.now();
        withAttention(attention("stale", null, now.minusDays(20)));
        List<NotificationItem> first = service.awaitingPush(ALICE);
        assertThat(first).hasSize(1);

        service.markPushed(ALICE, first.stream().map(NotificationItem::key).toList(), now);

        assertThat(service.awaitingPush(ALICE)).isEmpty();
        assertThat(service.inbox(ALICE).unread())
                .as("a ring is not a read: the item is still waiting in the app")
                .isEqualTo(1);

        withAttention(attention("stale", null, now.minusDays(19)));

        assertThat(service.awaitingPush(ALICE)).extracting(NotificationItem::key)
                .containsExactly("stale:" + APP + ":"
                        + now.minusDays(19).toInstant().getEpochSecond());
    }

    @Test
    void a_saved_search_with_new_matches_is_one_item_keyed_by_the_newest_arrival() {
        OffsetDateTime newest = OffsetDateTime.parse("2026-10-29T03:00:00Z");
        when(savedSearches.alerts(eq(ALICE), any())).thenReturn(List.of(
                new SavedSearchMatcher.Alert(SEARCH, "Backend roles in Berlin", 4, newest,
                        "/jobs?q=backend&location=Berlin")));

        Inbox inbox = service.inbox(ALICE);

        assertThat(inbox.items()).hasSize(1);
        NotificationItem item = inbox.items().get(0);
        assertThat(item.kind()).isEqualTo(NotificationService.KIND_SAVED_SEARCH);
        assertThat(item.title()).isEqualTo("Backend roles in Berlin");
        assertThat(item.count()).isEqualTo(4);
        assertThat(item.link()).isEqualTo("/jobs?q=backend&location=Berlin");
        assertThat(item.key()).isEqualTo("saved_search:" + SEARCH + ":"
                + newest.toInstant().getEpochSecond());
        assertThat(item.at()).isEqualTo(newest);
        assertThat(item.read()).isFalse();
        assertThat(service.awaitingDelivery(ALICE)).extracting(NotificationItem::kind)
                .containsExactly(NotificationService.KIND_SAVED_SEARCH);
    }

    @Test
    void a_dismissed_search_alert_stays_away_until_a_newer_posting_matches() {
        OffsetDateTime first = OffsetDateTime.now().minusHours(2);
        when(savedSearches.alerts(eq(ALICE), any())).thenReturn(List.of(
                new SavedSearchMatcher.Alert(SEARCH, "Backend roles", 2, first, "/jobs?q=backend")));
        String key = service.inbox(ALICE).items().get(0).key();

        assertThat(service.dismiss(ALICE, key).items()).isEmpty();

        OffsetDateTime second = OffsetDateTime.now().minusMinutes(5);
        when(savedSearches.alerts(eq(ALICE), any())).thenReturn(List.of(
                new SavedSearchMatcher.Alert(SEARCH, "Backend roles", 1, second, "/jobs?q=backend")));
        Inbox after = service.inbox(ALICE);

        assertThat(after.unread()).isEqualTo(1);
        assertThat(after.items().get(0).key()).endsWith(":"
                + second.toInstant().getEpochSecond());
        assertThat(after.items().get(0).count()).isEqualTo(1);
    }

    private static NotificationState state(String key, OffsetDateTime readAt,
                                           OffsetDateTime dismissedAt) {
        NotificationState state = new NotificationState();
        state.setUserId(ALICE);
        state.setSignalKey(key);
        state.setReadAt(readAt);
        state.setDismissedAt(dismissedAt);
        return state;
    }
}
