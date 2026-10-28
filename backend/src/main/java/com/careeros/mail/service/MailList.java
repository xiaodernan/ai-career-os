package com.careeros.mail.service;

import com.careeros.mail.entity.MailPreference;
import java.util.Locale;

/**
 * The two letters a reader can turn off, named by what the page prints rather than by the
 * class that composes them (roadmap 23.1).
 *
 * <p>The slug is the URL segment a mail client's one-click POST carries and the column the
 * sweep reads, so one spelling runs from the letter's header through the page to the query.
 */
public enum MailList {

    /** The Monday letter: the week in applications. */
    WEEKLY("weekly"),

    /** The morning signals: unread inbox items, mailed once per episode. */
    SIGNALS("signals");

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
        return this == WEEKLY ? row.isWeeklyDigest() : row.isSignalMail();
    }

    void apply(MailPreference row, boolean enabled) {
        if (this == WEEKLY) {
            row.setWeeklyDigest(enabled);
        } else {
            row.setSignalMail(enabled);
        }
    }
}
