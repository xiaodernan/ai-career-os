package com.careeros.calendar.service;

import com.careeros.application.entity.Application;
import com.careeros.application.repository.ApplicationRepository;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Locale;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * The reader's board, read as a calendar (roadmap 34).
 *
 * <p>Only rows that carry a {@code reminder_at} become events: the reminder is the one time
 * the reader explicitly wrote down, and inventing events from {@code applied_at} or the
 * board's own ordering would put times on the calendar that nobody asked for. Past reminders
 * stay in the document -- the feed is a faithful mirror of the board, so an event leaves the
 * calendar when the reader clears the reminder, not when the date slips by.
 */
@Service
public class CalendarService {

    private final ApplicationRepository applications;
    private final CalendarLinks links;

    public CalendarService(ApplicationRepository applications, CalendarLinks links) {
        this.applications = applications;
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
        boolean chinese = locale != null && locale.toLowerCase(Locale.ROOT).startsWith("zh");
        return CalendarFeed.render(
                reminders,
                chinese ? "职业提醒" : "Career OS reminders",
                chinese ? "来自 Career OS 的申请提醒。" : "Your application follow-ups from Career OS.",
                links.webRoot() + "/applications");
    }

    private static CalendarFeed.Reminder reminder(Application application) {
        return new CalendarFeed.Reminder(
                application.getId(),
                application.getTitle(),
                application.getCompanyName(),
                application.getReminderAt(),
                stamp(application));
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
