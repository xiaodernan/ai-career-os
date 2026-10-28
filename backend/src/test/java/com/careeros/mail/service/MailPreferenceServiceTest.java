package com.careeros.mail.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.mail.entity.MailPreference;
import com.careeros.mail.repository.MailPreferenceRepository;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

/**
 * The reader's answer about the two letters (roadmap 23.1).
 *
 * <p>Three claims. An account with no row receives both letters -- the default is why signup
 * writes nothing, and a sweep that read absence as "off" would silence every new account. A
 * first change creates the row with the other letter still on, so turning off the Monday letter
 * is not also turning off the morning signals. And the opt-out set a sweep subtracts is read
 * from the column for that letter, not from the row's existence.
 */
class MailPreferenceServiceTest {

    private static final UUID ALICE = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final UUID BOB = UUID.fromString("22222222-2222-4222-8222-222222222222");

    private MailPreferenceRepository repository;
    private MailPreferenceService service;

    @BeforeEach
    void setUp() {
        repository = mock(MailPreferenceRepository.class);
        service = new MailPreferenceService(repository);
        when(repository.findById(ALICE)).thenReturn(Optional.empty());
    }

    @Test
    void anAccountWithNoRowReceivesBothLetters() {
        assertThat(service.receives(ALICE, MailList.WEEKLY)).isTrue();
        assertThat(service.receives(ALICE, MailList.SIGNALS)).isTrue();
    }

    @Test
    void theFirstChangeCreatesTheRowWithTheOtherLetterStillOn() {
        service.set(ALICE, MailList.WEEKLY, false);

        ArgumentCaptor<MailPreference> saved = ArgumentCaptor.forClass(MailPreference.class);
        verify(repository).save(saved.capture());
        assertThat(saved.getValue().getUserId()).isEqualTo(ALICE);
        assertThat(saved.getValue().isWeeklyDigest()).isFalse();
        assertThat(saved.getValue().isSignalMail())
                .as("turning off one letter must not turn off the other")
                .isTrue();
    }

    @Test
    void aSecondChangeFlipsOnlyItsOwnColumn() {
        MailPreference row = new MailPreference();
        row.setUserId(BOB);
        row.setSignalMail(false);
        when(repository.findById(BOB)).thenReturn(Optional.of(row));

        service.set(BOB, MailList.WEEKLY, false);

        verify(repository).save(row);
        assertThat(row.isWeeklyDigest()).isFalse();
        assertThat(row.isSignalMail()).isFalse();
    }

    @Test
    void turningALetterBackOnWritesTheRowRatherThanDeletingIt() {
        MailPreference row = new MailPreference();
        row.setUserId(ALICE);
        row.setWeeklyDigest(false);
        when(repository.findById(ALICE)).thenReturn(Optional.of(row));

        service.set(ALICE, MailList.WEEKLY, true);

        verify(repository).save(row);
        assertThat(row.isWeeklyDigest()).isTrue();
        assertThat(service.receives(ALICE, MailList.WEEKLY)).isTrue();
    }

    @Test
    void theOptedOutSetComesFromTheColumnForThatLetter() {
        MailPreference weeklyOff = new MailPreference();
        weeklyOff.setUserId(ALICE);
        weeklyOff.setWeeklyDigest(false);
        when(repository.findByWeeklyDigestFalse()).thenReturn(List.of(weeklyOff));
        MailPreference signalsOff = new MailPreference();
        signalsOff.setUserId(BOB);
        signalsOff.setSignalMail(false);
        when(repository.findBySignalMailFalse()).thenReturn(List.of(signalsOff));

        assertThat(service.optedOut(MailList.WEEKLY)).containsExactly(ALICE);
        assertThat(service.optedOut(MailList.SIGNALS)).containsExactly(BOB);
        verify(repository, never()).findAll();
    }
}
