package com.careeros.report.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.careeros.application.entity.Application;
import com.careeros.application.repository.ApplicationRepository;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;

/**
 * The card a restored row may point at (roadmap 56.5).
 *
 * <p>The bundle's {@code application_id} is a foreign key into the caller's
 * own cards. A restore into a fresh account has none of them, so the link is
 * written only when the target owns the card -- and dropped otherwise. The
 * row still lands either way: the reader asked for the rehearsal, not for the
 * link.
 */
class ImportServiceCardLinkTest {

    private final ApplicationRepository applications = mock(ApplicationRepository.class);
    private final UUID userId = UUID.randomUUID();

    @Test
    void theLinkIsKeptWhenTheCallerOwnsTheCard() {
        UUID card = UUID.randomUUID();
        when(applications.findByIdAndUserId(card, userId))
                .thenReturn(Optional.of(mock(Application.class)));

        assertThat(ImportService.cardLink(card, userId, applications)).isEqualTo(card);
    }

    @Test
    void theLinkIsDroppedWhenTheCardIsSomebodyElses() {
        UUID card = UUID.randomUUID();
        when(applications.findByIdAndUserId(card, userId)).thenReturn(Optional.empty());

        assertThat(ImportService.cardLink(card, userId, applications)).isNull();
    }

    @Test
    void aBundleThatNamesNoCardHasNoLinkToWrite() {
        assertThat(ImportService.cardLink(null, userId, applications)).isNull();
    }
}