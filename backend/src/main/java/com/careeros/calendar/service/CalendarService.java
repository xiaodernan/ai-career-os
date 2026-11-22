package com.careeros.calendar.service;

import com.careeros.application.entity.Application;
import com.careeros.application.repository.ApplicationRepository;
import com.careeros.common.Paging;
import com.careeros.knowledge.entity.UserNote;
import com.careeros.knowledge.repository.UserNoteRepository;
import com.careeros.offer.entity.OfferRow;
import com.careeros.offer.repository.OfferShelfRepository;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.Objects;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * The reader's board, read as a calendar (roadmap 34, offer deadlines in Epic 196).
 *
 * <p>Only rows that carry a {@code reminder_at} become application events, and only pending
 * offers that carry a {@code deadline} become decision events: the reminder is the one time
 * the reader explicitly wrote down, and a decided offer is no longer a question. Past
 * reminders stay in the document -- the feed is a faithful mirror of the board, so an event
 * leaves the calendar when the reader clears the reminder, not when the date slips by.
 */
@Service
public class CalendarService {

    private final ApplicationRepository applications;
    private final OfferShelfRepository offers;
    private final UserNoteRepository notes;
    private final CalendarLinks links;

    public CalendarService(ApplicationRepository applications, OfferShelfRepository offers,
                           UserNoteRepository notes, CalendarLinks links) {
        this.applications = applications;
        this.offers = offers;
        this.notes = notes;
        this.links = links;
    }

    /** The document for one account, written in the language the account reads. */
    @Transactional(readOnly = true)
    public String feed(UUID userId, String locale) {
        List<CalendarFeed.Reminder> reminders = applications
                .findByUserIdAndReminderAtIsNotNullOrderByReminderAtAscIdAsc(userId)
                .stream()
                .map(CalendarService::reminder)
                .toList();
        List<CalendarFeed.Deadline> deadlines = offers
                .findByUserIdAndDecisionAndDeadlineIsNotNullOrderByDeadlineAsc(userId, "pending")
                .stream()
                .map(CalendarService::deadline)
                .toList();
        // Epic 387: a sealed letter is a dated fact too. The note's body never reaches
        // the feed — only its opening day and the way back to the timeline.
        List<CalendarFeed.Capsule> capsules = notes
                .findByTag(userId, "capsule", Paging.first(200))
                .getContent()
                .stream()
                .map(CalendarService::capsule)
                .filter(Objects::nonNull)
                .sorted(Comparator.comparing(CalendarFeed.Capsule::date))
                .toList();
        boolean chinese = locale != null && locale.toLowerCase(Locale.ROOT).startsWith("zh");
        return CalendarFeed.render(
                reminders,
                deadlines,
                capsules,
                chinese ? "职业日历" : "Career OS calendar",
                chinese ? "来自 Career OS 的申请提醒、录用决定截止日期与封存的信。"
                        : "Your application follow-ups, offer decision deadlines and sealed letters from Career OS.",
                links.webRoot() + "/applications",
                links.webRoot() + "/offers",
                links.webRoot() + "/timeline",
                chinese);
    }

    private static CalendarFeed.Reminder reminder(Application application) {
        return new CalendarFeed.Reminder(
                application.getId(),
                application.getTitle(),
                application.getCompanyName(),
                application.getReminderAt(),
                stamp(application));
    }

    private static CalendarFeed.Deadline deadline(OfferRow offer) {
        return new CalendarFeed.Deadline(
                offer.getId(),
                offer.getLabel(),
                offer.getDeadline(),
                stamp(offer));
    }

    /**
     * A capsule note becomes its opening day, or null when the tag is not a real
     * date. The stamp is the note's last change, so an edited letter does not
     * rewrite the event; a row the database has not stamped falls back to the day.
     */
    private static CalendarFeed.Capsule capsule(UserNote note) {
        LocalDate date = CalendarFeed.capsuleDate(note.getTags());
        if (date == null) {
            return null;
        }
        OffsetDateTime stamp = note.getUpdatedAt() != null ? note.getUpdatedAt()
                : note.getCreatedAt() != null ? note.getCreatedAt()
                : date.atStartOfDay().atOffset(ZoneOffset.UTC);
        return new CalendarFeed.Capsule(note.getId(), date, stamp);
    }

    private static OffsetDateTime stamp(OfferRow offer) {
        if (offer.getUpdatedAt() != null) {
            return offer.getUpdatedAt();
        }
        if (offer.getCreatedAt() != null) {
            return offer.getCreatedAt();
        }
        return offer.getDeadline();
    }

    /**
     * When the event was last changed. {@code updated_at} covers an edited reminder and a
     * moved card alike; a row the database has not stamped yet falls back to its creation,
     * and finally to the reminder itself, so the document never carries a missing date.
     */
    private static OffsetDateTime stamp(Application application) {
        if (application.getUpdatedAt() != null) {
            return application.getUpdatedAt();
        }
        if (application.getCreatedAt() != null) {
            return application.getCreatedAt();
        }
        return application.getReminderAt();
    }
}
