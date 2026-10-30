package com.careeros.mail.service;

import com.careeros.mail.entity.MailPreference;
import java.util.Locale;

/**
 * The three letters a reader can turn off, named by what the page prints rather than by the
 * class that composes them (roadmap 23.1, 41.1).
 *
 * <p>The slug is the URL segment a mail client's one-click POST carries and the column the
 * sweep reads, so one spelling runs from the letter's header through the page to the query.
 */
public enum MailList {

    /** The Monday letter: the week in applications. */
    WEEKLY("weekly"),

    /** The morning signals: unread inbox items, mailed once per episode. */
    SIGNALS("signals"),

    /**
     * The reminder's own letter (roadmap 41.1): mailed when the reminder comes due, rather than
     * waiting for the morning. Off does not silence the reminder -- the morning signal letter
     * still carries it -- so this dial chooses the moment, not whether.
     */
    REMINDERS("reminders");

    private final String slug;

    MailList(String slug) {
        this.slug = slug;
    }

    public String slug() {
        return slug;
    }

    /** The list a URL segment names, or null when it names neither. */
    public static MailList of(String slug) {
        if (slug == null) {
            return null;
        }
        String normalized = slug.trim().toLowerCase(Locale.ROOT);
        for (MailList list : values()) {
            if (list.slug.equals(normalized)) {
                return list;
            }
        }
        return null;
    }

    /** Whether this list is on for a stored row; an absent row is handled by the service. */
    boolean allows(MailPreference row) {
        return switch (this) {
            case WEEKLY -> row.isWeeklyDigest();
            case SIGNALS -> row.isSignalMail();
            case REMINDERS -> row.isReminderMail();
        };
    }

    void apply(MailPreference row, boolean enabled) {
        switch (this) {
            case WEEKLY -> row.setWeeklyDigest(enabled);
            case SIGNALS -> row.setSignalMail(enabled);
            case REMINDERS -> row.setReminderMail(enabled);
        }
    }
}
