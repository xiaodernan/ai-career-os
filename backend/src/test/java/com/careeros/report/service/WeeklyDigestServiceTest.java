package com.careeros.report.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.same;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import com.careeros.application.repository.ApplicationRepository;
import com.careeros.auth.entity.User;
import com.careeros.auth.repository.UserRepository;
import com.careeros.report.dto.WeeklyDigestDtos.WeeklyDigestDto;
import com.careeros.report.entity.WeeklyDigest;
import com.careeros.report.repository.WeeklyDigestRepository;
import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.data.domain.Pageable;
import org.springframework.mail.MailSendException;
import org.springframework.test.util.ReflectionTestUtils;

/**
 * The weekly letter (roadmap 19.4) and the sweep that mails it (21.2).
 *
 * <p>What is worth pinning: the letter is about seven days, asked of the engine with that
 * window; a week has one letter, so composing it again refreshes the row instead of filing a
 * second; a week always starts on Monday, because that is the only week-start the table
 * accepts; one account's failure does not cost the others their night; and the Monday sweep
 * mails each letter to its own account once -- a recomposed week that already left is not
 * mailed twice, and a refused letter is recorded on the row rather than thrown into the sweep.
 */
class WeeklyDigestServiceTest {

    private static final UUID ALICE = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final UUID BOB = UUID.fromString("22222222-2222-4222-8222-222222222222");
    private static final UUID LETTER = UUID.fromString("33333333-3333-4333-8333-333333333333");

    private static final LocalDate WEEK = LocalDate.of(2026, 10, 26);

    private WeeklyDigestRepository digests;
    private ApplicationRepository applications;
    private AnalysisService analysis;
    private UserRepository users;
    private WeeklyDigestMailer mailer;
    private WeeklyDigestDeliveryMetrics metrics;
    private WeeklyDigestService service;

    @BeforeEach
    void setUp() {
        digests = mock(WeeklyDigestRepository.class);
        applications = mock(ApplicationRepository.class);
        analysis = mock(AnalysisService.class);
        users = mock(UserRepository.class);
        mailer = mock(WeeklyDigestMailer.class);
        metrics = mock(WeeklyDigestDeliveryMetrics.class);
        service = new WeeklyDigestService(digests, applications, analysis, users, mailer, metrics);
        when(digests.save(any(WeeklyDigest.class))).thenAnswer(invocation -> {
            WeeklyDigest letter = invocation.getArgument(0);
            if (letter.getId() == null) {
                ReflectionTestUtils.setField(letter, "id", LETTER);
            }
            return letter;
        });
    }

    @Test
    void aLetterIsAboutSevenDaysAndTheEngineIsAskedForThatWindow() {
        when(analysis.insightDigest(ALICE, "en", 7))
                .thenReturn(Map.of("totalApplications", 4, "stalledCount", 1));
        when(digests.findByUserIdAndWeekStart(eq(ALICE), any())).thenReturn(Optional.empty());

        WeeklyDigestDto letter = service.composeNow(ALICE);

        assertThat(letter.weekStart()).isEqualTo(
                WeeklyDigestService.weekStartOf(LocalDate.now(ZoneOffset.UTC)));
        assertThat(letter.weekStart().getDayOfWeek()).isEqualTo(DayOfWeek.MONDAY);
        assertThat(letter.windowDays()).isEqualTo(7);
        assertThat(letter.generatedAt()).isNotNull();
        assertThat(letter.payload()).containsEntry("totalApplications", 4);
        verify(analysis).insightDigest(ALICE, "en", 7);
    }

    @Test
    void theLetterIsWrittenInTheAccountsLanguage() {
        User chinese = account(ALICE, "alice@example.com");
        chinese.setLocale("zh");
        when(users.findById(ALICE)).thenReturn(Optional.of(chinese));
        when(analysis.insightDigest(ALICE, "zh", 7)).thenReturn(Map.of("totalApplications", 2));
        when(digests.findByUserIdAndWeekStart(eq(ALICE), any())).thenReturn(Optional.empty());

        WeeklyDigestDto letter = service.compose(ALICE, WEEK);

        verify(analysis).insightDigest(ALICE, "zh", 7);
        assertThat(letter.weekStart()).isEqualTo(WEEK);
        ArgumentCaptor<WeeklyDigest> written = ArgumentCaptor.forClass(WeeklyDigest.class);
        verify(digests).save(written.capture());
        assertThat(written.getValue().getLocale()).isEqualTo("zh");
    }

    @Test
    void recomposingAWeekRefreshesItsOneLetterRatherThanFilingASecond() {
        WeeklyDigest existing = new WeeklyDigest();
        existing.setUserId(ALICE);
        existing.setWeekStart(WEEK);
        existing.setWindowDays(7);
        existing.setPayload(Map.of("totalApplications", 1));
        ReflectionTestUtils.setField(existing, "id", LETTER);
        when(digests.findByUserIdAndWeekStart(ALICE, WEEK)).thenReturn(Optional.of(existing));
        when(analysis.insightDigest(ALICE, "en", 7))
                .thenReturn(Map.of("totalApplications", 4, "stalledCount", 2));

        WeeklyDigestDto letter = service.compose(ALICE, WEEK);

        assertThat(letter.id()).isEqualTo(LETTER);
        assertThat(letter.payload()).containsEntry("totalApplications", 4);
        verify(digests).save(existing);
        // One row, refreshed: a second insert would be a second save call.
        verify(digests, times(1)).save(any(WeeklyDigest.class));
    }

    @Test
    void oneAccountsFailureDoesNotCostTheOthersTheirLetter() {
        when(applications.distinctUserIds()).thenReturn(List.of(ALICE, BOB));
        when(analysis.insightDigest(eq(ALICE), any(), eq(7)))
                .thenThrow(new IllegalStateException("the engine is down"));
        when(analysis.insightDigest(eq(BOB), any(), eq(7)))
                .thenReturn(Map.of("totalApplications", 2));
        when(digests.findByUserIdAndWeekStart(eq(BOB), any())).thenReturn(Optional.empty());

        int written = service.composeWeek(WEEK);

        assertThat(written).isEqualTo(1);
        // Alice's previous letter, if any, was never even read: the failed engine call came first.
        verify(digests, never()).findByUserIdAndWeekStart(eq(ALICE), any());
        verify(digests).save(any(WeeklyDigest.class));
    }

    @Test
    void theHistoryIsTheNewestTwelveWeeks() {
        WeeklyDigest newest = new WeeklyDigest();
        newest.setWeekStart(WEEK);
        newest.setWindowDays(7);
        newest.setPayload(Map.of("totalApplications", 4));
        ReflectionTestUtils.setField(newest, "id", LETTER);
        when(digests.findByUserIdOrderByWeekStartDescIdDesc(eq(ALICE), any(Pageable.class)))
                .thenReturn(List.of(newest));

        List<WeeklyDigestDto> history = service.recent(ALICE);

        assertThat(history).hasSize(1);
        assertThat(history.get(0).weekStart()).isEqualTo(WEEK);
        assertThat(history.get(0).payload()).containsEntry("totalApplications", 4);
        ArgumentCaptor<Pageable> window = ArgumentCaptor.forClass(Pageable.class);
        verify(digests).findByUserIdOrderByWeekStartDescIdDesc(eq(ALICE), window.capture());
        assertThat(window.getValue().getPageNumber()).isZero();
        assertThat(window.getValue().getPageSize()).isEqualTo(12);
    }

    @Test
    void aWeekAlwaysStartsOnMonday() {
        assertThat(WeeklyDigestService.weekStartOf(LocalDate.of(2026, 10, 28)))
                .isEqualTo(LocalDate.of(2026, 10, 26));
        assertThat(WeeklyDigestService.weekStartOf(LocalDate.of(2026, 10, 26)))
                .isEqualTo(LocalDate.of(2026, 10, 26));
        assertThat(WeeklyDigestService.weekStartOf(LocalDate.of(2026, 11, 1)))
                .isEqualTo(LocalDate.of(2026, 10, 26));
    }

    @Test
    void thePayloadIsKeptAsTheEngineAnsweredIt() {
        Map<String, Object> answer = new HashMap<>();
        answer.put("totalApplications", 3);
        answer.put("stalled", List.of(Map.of("title", "Backend Engineer", "daysSinceLastActivity", 9)));
        answer.put("signals", List.of("3 application(s) have gone quiet past 7 days."));
        when(analysis.insightDigest(ALICE, "en", 7)).thenReturn(answer);
        when(digests.findByUserIdAndWeekStart(eq(ALICE), any())).thenReturn(Optional.empty());

        WeeklyDigestDto letter = service.compose(ALICE, WEEK);

        assertThat(letter.payload()).isSameAs(answer);
    }

    @Test
    void theNightMailsEachLetterToItsOwnAddressAndKeepsTheReceipt() {
        when(applications.distinctUserIds()).thenReturn(List.of(ALICE, BOB));
        when(analysis.insightDigest(eq(ALICE), any(), eq(7))).thenReturn(Map.of("totalApplications", 3));
        when(analysis.insightDigest(eq(BOB), any(), eq(7))).thenReturn(Map.of("totalApplications", 1));
        when(digests.findByUserIdAndWeekStart(eq(ALICE), any())).thenReturn(Optional.empty());
        when(digests.findByUserIdAndWeekStart(eq(BOB), any())).thenReturn(Optional.empty());
        when(users.findById(ALICE)).thenReturn(Optional.of(account(ALICE, "alice@example.com")));
        when(users.findById(BOB)).thenReturn(Optional.of(account(BOB, "bob@example.com")));

        int written = service.composeWeek(WEEK);

        assertThat(written).isEqualTo(2);
        ArgumentCaptor<WeeklyDigest> mailed = ArgumentCaptor.forClass(WeeklyDigest.class);
        verify(mailer).send(eq("alice@example.com"), mailed.capture());
        verify(mailer).send(eq("bob@example.com"), any(WeeklyDigest.class));
        assertThat(mailed.getValue().getUserId()).isEqualTo(ALICE);
        assertThat(mailed.getValue().getDeliveredAt()).isNotNull();
        assertThat(mailed.getValue().getDeliveryAttempts()).isEqualTo(1);
        assertThat(mailed.getValue().getDeliveryError()).isNull();
        verify(metrics, times(2)).recordSent(any());
        verify(metrics, never()).recordRefused();
    }

    @Test
    void aWeekThatAlreadyLeftIsNotMailedAgainWhenItIsRecomposed() {
        WeeklyDigest delivered = new WeeklyDigest();
        delivered.setUserId(ALICE);
        delivered.setWeekStart(WEEK);
        delivered.setWindowDays(7);
        delivered.setPayload(Map.of("totalApplications", 2));
        delivered.setDeliveredAt(OffsetDateTime.now(ZoneOffset.UTC).minusDays(2));
        delivered.setDeliveryAttempts(1);
        when(applications.distinctUserIds()).thenReturn(List.of(ALICE));
        when(analysis.insightDigest(eq(ALICE), any(), eq(7))).thenReturn(Map.of("totalApplications", 4));
        when(digests.findByUserIdAndWeekStart(ALICE, WEEK)).thenReturn(Optional.of(delivered));
        when(users.findById(ALICE)).thenReturn(Optional.of(account(ALICE, "alice@example.com")));

        int written = service.composeWeek(WEEK);

        assertThat(written).isEqualTo(1);
        verify(mailer, never()).send(anyString(), any(WeeklyDigest.class));
        assertThat(delivered.getDeliveryAttempts()).isEqualTo(1);
        assertThat(delivered.getPayload()).containsEntry("totalApplications", 4);
        verifyNoInteractions(metrics);
    }

    @Test
    void aRefusedLetterIsRecordedAndTheNightStillReachesTheOthers() {
        when(applications.distinctUserIds()).thenReturn(List.of(ALICE, BOB));
        when(analysis.insightDigest(eq(ALICE), any(), eq(7))).thenReturn(Map.of("totalApplications", 3));
        when(analysis.insightDigest(eq(BOB), any(), eq(7))).thenReturn(Map.of("totalApplications", 1));
        when(digests.findByUserIdAndWeekStart(eq(ALICE), any())).thenReturn(Optional.empty());
        when(digests.findByUserIdAndWeekStart(eq(BOB), any())).thenReturn(Optional.empty());
        when(users.findById(ALICE)).thenReturn(Optional.of(account(ALICE, "alice@example.com")));
        when(users.findById(BOB)).thenReturn(Optional.of(account(BOB, "bob@example.com")));
        ArgumentCaptor<WeeklyDigest> refused = ArgumentCaptor.forClass(WeeklyDigest.class);
        doThrow(new MailSendException("relay said 550")).when(mailer)
                .send(eq("alice@example.com"), refused.capture());

        int written = service.composeWeek(WEEK);

        assertThat(written).isEqualTo(2);
        verify(mailer).send(eq("bob@example.com"), any(WeeklyDigest.class));
        assertThat(refused.getValue().getDeliveryError()).contains("550");
        assertThat(refused.getValue().getDeliveredAt()).isNull();
        assertThat(refused.getValue().getDeliveryAttempts()).isEqualTo(1);
        verify(metrics).recordRefused();
        verify(metrics).recordSent(any());
    }

    @Test
    void anAccountWithNoRowIsSkippedAndNothingIsCounted() {
        when(applications.distinctUserIds()).thenReturn(List.of(ALICE));
        when(analysis.insightDigest(eq(ALICE), any(), eq(7))).thenReturn(Map.of("totalApplications", 3));
        when(digests.findByUserIdAndWeekStart(eq(ALICE), any())).thenReturn(Optional.empty());
        when(users.findById(ALICE)).thenReturn(Optional.empty());

        int written = service.composeWeek(WEEK);

        assertThat(written).isEqualTo(1);
        verify(mailer, never()).send(anyString(), any(WeeklyDigest.class));
        ArgumentCaptor<WeeklyDigest> saved = ArgumentCaptor.forClass(WeeklyDigest.class);
        verify(digests).save(saved.capture());
        assertThat(saved.getValue().getDeliveryAttempts()).isZero();
        assertThat(saved.getValue().getDeliveredAt()).isNull();
        verifyNoInteractions(metrics);
    }

    @Test
    void theRetryClockMailsAnAttemptedLetterAndCountsTheAttempt() {
        WeeklyDigest refused = letter(ALICE, WEEK, 1, "relay said 550");
        when(digests
                .findByDeliveredAtIsNullAndDeliveryAttemptsGreaterThanAndDeliveryAttemptsLessThanOrderByWeekStartAscIdAsc(
                        anyInt(), anyInt(), any(Pageable.class)))
                .thenReturn(List.of(refused));
        when(users.findById(ALICE)).thenReturn(Optional.of(account(ALICE, "alice@example.com")));

        int delivered = service.retryUndelivered();

        assertThat(delivered).isEqualTo(1);
        verify(mailer).send(eq("alice@example.com"), same(refused));
        assertThat(refused.getDeliveredAt()).isNotNull();
        assertThat(refused.getDeliveryError()).isNull();
        assertThat(refused.getDeliveryAttempts()).isEqualTo(2);
        verify(metrics).recordSent(any());

        ArgumentCaptor<Integer> above = ArgumentCaptor.forClass(Integer.class);
        ArgumentCaptor<Integer> below = ArgumentCaptor.forClass(Integer.class);
        ArgumentCaptor<Pageable> window = ArgumentCaptor.forClass(Pageable.class);
        verify(digests)
                .findByDeliveredAtIsNullAndDeliveryAttemptsGreaterThanAndDeliveryAttemptsLessThanOrderByWeekStartAscIdAsc(
                        above.capture(), below.capture(), window.capture());
        assertThat(above.getValue())
                .as("zero attempts is the dashboard's compose, which must never be mailed by the clock")
                .isZero();
        assertThat(below.getValue()).isEqualTo(5);
        assertThat(window.getValue().getPageSize()).isEqualTo(100);
    }

    @Test
    void theRetryClockLeavesALetterThatAlreadyHasItsReceipt() {
        WeeklyDigest delivered = letter(ALICE, WEEK, 2, "relay said 550");
        delivered.setDeliveredAt(OffsetDateTime.now(ZoneOffset.UTC).minusHours(3));
        when(digests
                .findByDeliveredAtIsNullAndDeliveryAttemptsGreaterThanAndDeliveryAttemptsLessThanOrderByWeekStartAscIdAsc(
                        anyInt(), anyInt(), any(Pageable.class)))
                .thenReturn(List.of(delivered));

        int sent = service.retryUndelivered();

        assertThat(sent).isZero();
        verify(mailer, never()).send(anyString(), any(WeeklyDigest.class));
        verifyNoInteractions(metrics);
    }

    @Test
    void theRetryClockDoesNotLetOneRefusalStopTheNextLetter() {
        WeeklyDigest alice = letter(ALICE, WEEK, 1, "relay said 550");
        WeeklyDigest bob = letter(BOB, WEEK.minusWeeks(1), 2, "relay said 421");
        when(digests
                .findByDeliveredAtIsNullAndDeliveryAttemptsGreaterThanAndDeliveryAttemptsLessThanOrderByWeekStartAscIdAsc(
                        anyInt(), anyInt(), any(Pageable.class)))
                .thenReturn(List.of(alice, bob));
        when(users.findById(ALICE)).thenReturn(Optional.of(account(ALICE, "alice@example.com")));
        when(users.findById(BOB)).thenReturn(Optional.of(account(BOB, "bob@example.com")));
        doThrow(new MailSendException("relay still says 550")).when(mailer)
                .send(eq("alice@example.com"), any(WeeklyDigest.class));

        int delivered = service.retryUndelivered();

        assertThat(delivered).isEqualTo(1);
        assertThat(alice.getDeliveryError()).contains("still says 550");
        assertThat(alice.getDeliveryAttempts()).isEqualTo(2);
        assertThat(bob.getDeliveredAt()).isNotNull();
        verify(metrics).recordRefused();
        verify(metrics).recordSent(any());
    }

    private static WeeklyDigest letter(UUID userId, LocalDate week, int attempts, String error) {
        WeeklyDigest letter = new WeeklyDigest();
        letter.setUserId(userId);
        letter.setWeekStart(week);
        letter.setWindowDays(7);
        letter.setPayload(Map.of("totalApplications", 3));
        letter.setDeliveryAttempts(attempts);
        letter.setDeliveryError(error);
        return letter;
    }

    private static User account(UUID id, String email) {
        User user = new User();
        user.setId(id);
        user.setEmail(email);
        return user;
    }
}
