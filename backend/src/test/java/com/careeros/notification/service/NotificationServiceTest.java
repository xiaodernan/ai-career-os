package com.careeros.notification.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.careeros.job.entity.IngestionFeed;
import com.careeros.job.entity.IngestionRun;
import com.careeros.job.repository.IngestionFeedRepository;
import com.careeros.job.repository.IngestionRunRepository;
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

    private DashboardRepository dashboard;
    private IngestionRunRepository runs;
    private IngestionFeedRepository feeds;
    private NotificationStateRepository states;
    private Map<String, NotificationState> store;
    private NotificationService service;

    @BeforeEach
    void setUp() {
        dashboard = mock(DashboardRepository.class);
        runs = mock(IngestionRunRepository.class);
        feeds = mock(IngestionFeedRepository.class);
        states = mock(NotificationStateRepository.class);
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

        service = new NotificationService(dashboard, runs, feeds, states);
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
