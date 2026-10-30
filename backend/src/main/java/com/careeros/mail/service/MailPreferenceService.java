package com.careeros.mail.service;

import com.careeros.mail.entity.MailPreference;
import com.careeros.mail.repository.MailPreferenceRepository;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * The reader's answer about the letters (roadmap 23.1, 41.1).
 *
 * <p>An account with no row receives all of them: the default is the reason signup writes
 * nothing and the reason a reader who never opened this page is not a special case in any
 * sweep. Turning a list off writes the row (or the column) and is idempotent; turning it back
 * on flips the same column rather than deleting the row, so "asked twice" leaves the same
 * evidence as "asked once".
 *
 * <p>Every surface asks the same question. The sweeps read the opt-out set once per pass, while
 * a single delivery asks {@link #receives}; the two answers come from the same columns, so a
 * letter cannot be suppressed on the sweep and mailed by the retry.
 */
@Service
public class MailPreferenceService {

    private final MailPreferenceRepository preferences;

    public MailPreferenceService(MailPreferenceRepository preferences) {
        this.preferences = preferences;
    }

    /** Whether this account still receives the named letter; no row means yes. */
    @Transactional(readOnly = true)
    public boolean receives(UUID userId, MailList list) {
        return preferences.findById(userId).map(list::allows).orElse(true);
    }

    /** The accounts that turned the named letter off, for a sweep to subtract from its audience. */
    @Transactional(readOnly = true)
    public Set<UUID> optedOut(MailList list) {
        return preferencesOf(list).stream()
                .map(MailPreference::getUserId)
                .collect(Collectors.toCollection(LinkedHashSet::new));
    }

    /**
     * Sets one dial and returns the state it now has. The row is created on the first change
     * with the other letter still on, so a reader who turned off the Monday letter has not
     * silently turned off the morning signal mail as a side effect.
     */
    @Transactional
    public boolean set(UUID userId, MailList list, boolean enabled) {
        MailPreference row = preferences.findById(userId).orElseGet(() -> {
            MailPreference fresh = new MailPreference();
            fresh.setUserId(userId);
            return fresh;
        });
        list.apply(row, enabled);
        preferences.save(row);
        return enabled;
    }

    private List<MailPreference> preferencesOf(MailList list) {
        return switch (list) {
            case WEEKLY -> preferences.findByWeeklyDigestFalse();
            case SIGNALS -> preferences.findBySignalMailFalse();
            case REMINDERS -> preferences.findByReminderMailFalse();
        };
    }
}
