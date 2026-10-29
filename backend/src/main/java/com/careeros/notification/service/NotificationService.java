package com.careeros.notification.service;

import com.careeros.common.Paging;
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
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * The inbox (roadmap 19.3): one place for the signals the platform already knows about.
 *
 * <p>There is no notifications table, and that is the design. Every item is read off a source
 * that is its own record -- an open application whose reminder has come due or that has been
 * quiet for the dashboard's own window, a pull the nightly sweep filed, a saved search the
 * board has new postings for -- so an item can never disagree with the screen that shows the
 * same thing, and a source that disappears takes its item with it. The only state stored is
 * the reader's: {@link NotificationState}, keyed by the episode, not by the row.
 *
 * <p>Acting on the inbox is scoped to what it is showing. A read or dismissed key that is not
 * among the current items is ignored, which keeps a stale browser tab from filing state for a
 * signal that already ended, and keeps the table from growing with keys nobody was ever shown.
 *
 * <p>The screen is not the only surface a signal reaches (roadmap 22.1). The morning sweep asks
 * this service which items are still waiting -- unread in the app and never carried out by mail
 * -- so the letter and the inbox cannot describe different mornings, and records the mail's
 * acceptance on the same episode row that remembers the read. A signal that was read or
 * dismissed in the app is not mailed; a signal that was mailed is not mailed twice.
 *
 * <p>The ring outside the app is a second door with its own latch (roadmap 33.3). The browser
 * is woken for what is unread, undismissed and not yet pushed -- <em>not</em> for what has
 * already been mailed, because a reader who turned the letter off asked to be woken instead,
 * and a reader who has not opened the app since yesterday's letter is exactly who a ring is
 * for. The two latches never consult each other; each channel records only what its own
 * transport accepted.
 */
@Service
public class NotificationService {

    /** The dashboard's "needs attention" window, asked of the same query. */
    static final int STALE_DAYS = 14;
    static final int ATTENTION_LIMIT = 20;
    static final int RUN_WINDOW = 20;
    /** A night older than this is history; the run list still shows it. */
    static final int LOOKBACK_DAYS = 7;
    /** What one screen can show before the inbox is a wall. */
    static final int INBOX_LIMIT = 40;
    static final int KEY_LIMIT = 160;

    public static final String KIND_REMINDER = "reminder";
    public static final String KIND_STALE = "stale";
    public static final String KIND_INGESTION_FAILED = "ingestion_failed";
    public static final String KIND_INGESTION_CREATED = "ingestion_created";
    /** A saved search whose question the board answered with postings it had not seen (29.1). */
    public static final String KIND_SAVED_SEARCH = "saved_search";

    private static final String INGESTION_PAGE = "/ingestion";

    private final DashboardRepository dashboard;
    private final IngestionRunRepository runs;
    private final IngestionFeedRepository feeds;
    private final SavedSearchMatcher savedSearches;
    private final NotificationStateRepository states;

    public NotificationService(DashboardRepository dashboard, IngestionRunRepository runs,
                               IngestionFeedRepository feeds, SavedSearchMatcher savedSearches,
                               NotificationStateRepository states) {
        this.dashboard = dashboard;
        this.runs = runs;
        this.feeds = feeds;
        this.savedSearches = savedSearches;
        this.states = states;
    }

    @Transactional(readOnly = true)
    public Inbox inbox(UUID userId) {
        List<NotificationItem> items = shown(userId).stream().map(Shown::item).toList();
        int unread = (int) items.stream().filter(item -> !item.read()).count();
        return new Inbox(items, unread, OffsetDateTime.now());
    }

    /**
     * What the morning mail may carry (roadmap 22.1): the items the inbox is showing that the
     * reader has neither read in the app nor already received by mail. Dismissed items are not
     * here because the reader said they did not want them; read items are not here because the
     * mailbox would be telling the reader something they already saw. The list is the screen's
     * own, same order and same cap, so the letter and the inbox describe the same morning.
     */
    @Transactional(readOnly = true)
    public List<NotificationItem> awaitingDelivery(UUID userId) {
        return shown(userId).stream()
                .filter(entry -> !entry.item().read())
                .filter(entry -> entry.state() == null || entry.state().getNotifiedAt() == null)
                .map(Shown::item)
                .toList();
    }

    /**
     * Latches the moment a mail carrying these episodes was accepted by the transport. A failed
     * send latches nothing, so the next sweep will try again; a latch never clears, so a second
     * sweep over the same morning cannot put a second copy in the mailbox. The keys come from
     * {@link #awaitingDelivery}, which is what makes them episodes the reader was shown.
     */
    @Transactional
    public void markNotified(UUID userId, List<String> keys, OffsetDateTime at) {
        for (String key : keys) {
            NotificationState state = stateFor(userId, key);
            state.setNotifiedAt(at);
            states.save(state);
        }
    }

    /**
     * What a ring may wake the account for (roadmap 33.3): the items the inbox is showing that
     * the reader has neither read nor dismissed and that no browser has been woken for. The mail
     * latch is deliberately not consulted -- see the class note -- and neither is the mail stop
     * list, which belongs to a different door.
     */
    @Transactional(readOnly = true)
    public List<NotificationItem> awaitingPush(UUID userId) {
        return shown(userId).stream()
                .filter(entry -> !entry.item().read())
                .filter(entry -> entry.state() == null || entry.state().getPushedAt() == null)
                .map(Shown::item)
                .toList();
    }

    /**
     * Latches the morning a browser accepted the ring for these episodes. Called only when at
     * least one registration took it: an account whose every browser refused is not remembered
     * as rung, so the next morning tries again. The latch never clears and is per episode, so a
     * new signal arrives under a new key with no latch.
     */
    @Transactional
    public void markPushed(UUID userId, List<String> keys, OffsetDateTime at) {
        for (String key : keys) {
            NotificationState state = stateFor(userId, key);
            state.setPushedAt(at);
            states.save(state);
        }
    }

    /** Marks the named items read; keys the inbox is not showing are ignored. */
    @Transactional
    public Inbox markRead(UUID userId, List<String> keys) {
        Map<String, NotificationItem> visible = visibleByKey(userId);
        OffsetDateTime now = OffsetDateTime.now();
        for (String raw : keys) {
            NotificationItem item = visible.get(raw == null ? "" : raw.trim());
            if (item == null || item.read()) {
                continue;
            }
            setRead(userId, item.key(), now);
        }
        return inbox(userId);
    }

    /** Marks every item the inbox is showing read. */
    @Transactional
    public Inbox markAllRead(UUID userId) {
        OffsetDateTime now = OffsetDateTime.now();
        for (NotificationItem item : visibleByKey(userId).values()) {
            if (!item.read()) {
                setRead(userId, item.key(), now);
            }
        }
        return inbox(userId);
    }

    /** Files one item away; it stays away until the signal becomes a new episode. */
    @Transactional
    public Inbox dismiss(UUID userId, String key) {
        NotificationItem item = visibleByKey(userId).get(key == null ? "" : key.trim());
        if (item != null) {
            NotificationState state = stateFor(userId, item.key());
            state.setDismissedAt(OffsetDateTime.now());
            states.save(state);
        }
        return inbox(userId);
    }

    private Map<String, NotificationItem> visibleByKey(UUID userId) {
        Map<String, NotificationItem> out = new LinkedHashMap<>();
        for (NotificationItem item : inbox(userId).items()) {
            out.putIfAbsent(item.key(), item);
        }
        return out;
    }

    /**
     * The one walk both surfaces share: every candidate the reader has not dismissed, newest
     * first, capped at what a screen can show, each paired with the state that was read for it
     * so the mail can tell an episode it has already carried from one it has not.
     */
    private List<Shown> shown(UUID userId) {
        Map<String, NotificationState> byKey = states.findByUserId(userId).stream()
                .collect(Collectors.toMap(NotificationState::getSignalKey, state -> state,
                        (first, second) -> first));
        List<Shown> visible = new ArrayList<>();
        for (Candidate candidate : candidates(userId)) {
            NotificationState state = byKey.get(candidate.key());
            if (state != null && state.getDismissedAt() != null) {
                continue;
            }
            visible.add(new Shown(candidate.item(state != null && state.getReadAt() != null), state));
        }
        visible.sort(Comparator.comparing(shown -> shown.item().at(),
                Comparator.nullsLast(Comparator.<OffsetDateTime>reverseOrder())));
        return visible.size() <= INBOX_LIMIT
                ? List.copyOf(visible)
                : List.copyOf(visible.subList(0, INBOX_LIMIT));
    }

    private void setRead(UUID userId, String key, OffsetDateTime now) {
        NotificationState state = stateFor(userId, key);
        state.setReadAt(now);
        states.save(state);
    }

    private NotificationState stateFor(UUID userId, String key) {
        return states.findByUserIdAndSignalKey(userId, key).orElseGet(() -> {
            NotificationState fresh = new NotificationState();
            fresh.setUserId(userId);
            fresh.setSignalKey(key);
            return fresh;
        });
    }

    /* ------------------------------------------------------------- synthesis */

    private List<Candidate> candidates(UUID userId) {
        List<Candidate> out = new ArrayList<>();
        for (AttentionItem item : dashboard.attention(userId, STALE_DAYS, ATTENTION_LIMIT)) {
            out.add(attention(item));
        }
        out.addAll(ingestion(userId));
        out.addAll(savedSearchAlerts(userId));
        return out;
    }

    /**
     * One waiting application as one item. The key carries the moment the episode began -- the
     * reminder date that came due, the last update that started the quiet window -- so a new
     * episode of the same kind arrives unread instead of inheriting a dismissal.
     */
    private static Candidate attention(AttentionItem item) {
        boolean due = "reminder_due".equals(item.reason());
        OffsetDateTime episode = due ? item.reminderAt() : item.updatedAt();
        OffsetDateTime at = due ? item.reminderAt()
                : item.updatedAt() == null ? null : item.updatedAt().plusDays(STALE_DAYS);
        String kind = due ? KIND_REMINDER : KIND_STALE;
        return new Candidate(
                kind + ":" + item.id() + ":" + (episode == null ? "" : episode.toInstant().getEpochSecond()),
                kind,
                text(item.title()),
                text(item.companyName()),
                text(item.status()),
                null,
                null,
                "/applications?application=" + item.id(),
                at);
    }

    /**
     * The last week's pulls that said something: a failure is always an item, and a night that
     * proposed postings is an item once; a quiet night that proposed nothing is the absence of
     * news, not a notification. Runs are newest first, so the lookback ends the walk.
     */
    private List<Candidate> ingestion(UUID userId) {
        Map<UUID, String> names = feeds.findByUserIdOrderByCreatedAtDesc(userId).stream()
                .collect(Collectors.toMap(IngestionFeed::getId, IngestionFeed::getName));
        OffsetDateTime cutoff = OffsetDateTime.now().minusDays(LOOKBACK_DAYS);
        List<Candidate> out = new ArrayList<>();
        for (IngestionRun run : runs.findByUserIdOrderByStartedAtDescIdDesc(
                userId, Paging.first(RUN_WINDOW)).getContent()) {
            OffsetDateTime started = run.getStartedAt();
            if (started == null || started.isBefore(cutoff)) {
                break;
            }
            String feed = names.getOrDefault(run.getFeedId(), "");
            String key = "ingestion:" + run.getId();
            if (IngestionRun.STATUS_FAILED.equals(run.getStatus())) {
                out.add(new Candidate(key, KIND_INGESTION_FAILED, feed, "", run.getStatus(),
                        null, run.getError(), INGESTION_PAGE, started));
                continue;
            }
            Integer created = createdOf(run);
            if (created != null && created > 0) {
                out.add(new Candidate(key, KIND_INGESTION_CREATED, feed, "", run.getStatus(),
                        created, null, INGESTION_PAGE, started));
            }
        }
        return out;
    }

    private static Integer createdOf(IngestionRun run) {
        Map<String, Object> counts = run.getCounts();
        if (counts == null) {
            return null;
        }
        return counts.get("create") instanceof Number number ? number.intValue() : null;
    }

    /**
     * A saved search the board has news for (roadmap 29.1): one item per search, keyed by the
     * newest matching posting's arrival. The episode is the arrival rather than the search, so
     * dismissing today's news leaves the search armed -- the next posting to match is a new
     * key, and therefore unread, without anything being stored to remember that it was armed.
     */
    private List<Candidate> savedSearchAlerts(UUID userId) {
        List<Candidate> out = new ArrayList<>();
        for (SavedSearchMatcher.Alert alert : savedSearches.alerts(userId, OffsetDateTime.now())) {
            out.add(new Candidate(
                    KIND_SAVED_SEARCH + ":" + alert.searchId() + ":"
                            + alert.newestAt().toInstant().getEpochSecond(),
                    KIND_SAVED_SEARCH, alert.name(), "", "", alert.count(), null, alert.link(),
                    alert.newestAt()));
        }
        return out;
    }

    private static String text(String value) {
        return Objects.toString(value, "");
    }

    /** One synthesized item before the reader's state is applied. */
    private record Candidate(String key, String kind, String title, String subject, String status,
                             Integer count, String note, String link, OffsetDateTime at) {

        NotificationItem item(boolean read) {
            return new NotificationItem(key, kind, title, subject, status, count, note, link, at, read);
        }
    }

    /** A visible item and the state row it was rendered from; null when the reader has no row. */
    private record Shown(NotificationItem item, NotificationState state) {
    }
}
