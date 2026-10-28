package com.careeros.mail.repository;

import com.careeros.mail.entity.MailPreference;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface MailPreferenceRepository extends JpaRepository<MailPreference, UUID> {

    /** Accounts that turned the Monday letter off; the query, not a scan, is the audience. */
    List<MailPreference> findByWeeklyDigestFalse();

    /** Accounts that turned the morning signals off. */
    List<MailPreference> findBySignalMailFalse();
}
