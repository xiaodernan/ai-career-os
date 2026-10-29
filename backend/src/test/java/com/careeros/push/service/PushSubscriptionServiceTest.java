package com.careeros.push.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.push.dto.PushDtos.PushSubscriptionItem;
import com.careeros.push.dto.PushDtos.PushSubscriptionRequest;
import com.careeros.push.entity.PushSubscription;
import com.careeros.push.repository.PushSubscriptionRepository;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

/**
 * What one browser registration stores (roadmap 33.1).
 *
 * <p>The endpoint is the registration, not the row: a re-subscribe -- a renewed key, a service
 * worker update, a different reader on the same browser -- must refresh and re-point the one
 * row, because two rows would ring that browser twice for one morning. The other half is the
 * refusal: a mangled address or key is refused here, with a code the settings switch can act
 * on, rather than stored and discovered by a failing send at 08:00.
 */
class PushSubscriptionServiceTest {

    private static final String ENDPOINT = "https://push.example.invalid/send/abc123";
    private static final String P256DH = "B".repeat(87);
    private static final String AUTH = "A".repeat(22);

    private final UUID userId = UUID.randomUUID();
    private final UUID otherUser = UUID.randomUUID();

    private PushSubscriptionRepository repository;
    private PushSubscriptionService service;

    @BeforeEach
    void setUp() {
        repository = mock(PushSubscriptionRepository.class);
        service = new PushSubscriptionService(repository);
        when(repository.save(any(PushSubscription.class))).thenAnswer(i -> i.getArgument(0));
    }

    private static PushSubscriptionRequest request(String endpoint, String p256dh, String auth,
            String label) {
        return new PushSubscriptionRequest(endpoint, p256dh, auth, label);
    }

    private PushSubscription saved() {
        ArgumentCaptor<PushSubscription> cap = ArgumentCaptor.forClass(PushSubscription.class);
        verify(repository).save(cap.capture());
        return cap.getValue();
    }

    @Test
    void aRegistrationIsStoredUnderTheCallerWithItsPaddingTrimmed() {
        PushSubscriptionItem item = service.register(userId, request(
                "  " + ENDPOINT + "  ", " " + P256DH + " ", " " + AUTH + " ", "  Work laptop  "));

        PushSubscription row = saved();
        assertThat(row.getUserId()).isEqualTo(userId);
        assertThat(row.getEndpointUrl()).isEqualTo(ENDPOINT);
        assertThat(row.getP256dh()).isEqualTo(P256DH);
        assertThat(row.getAuth()).isEqualTo(AUTH);
        assertThat(row.getLabel()).isEqualTo("Work laptop");
        assertThat(item.endpoint()).isEqualTo(ENDPOINT);
        assertThat(item.label()).isEqualTo("Work laptop");
    }

    @Test
    void reRegisteringTheSameEndpointRefreshesAndMovesTheRowRatherThanAddingOne() {
        PushSubscription keptByAnother = new PushSubscription();
        keptByAnother.setUserId(otherUser);
        keptByAnother.setEndpointUrl(ENDPOINT);
        keptByAnother.setP256dh("C".repeat(87));
        keptByAnother.setAuth("D".repeat(22));
        when(repository.findByEndpointUrl(ENDPOINT)).thenReturn(Optional.of(keptByAnother));

        service.register(userId, request(ENDPOINT, P256DH, AUTH, null));

        PushSubscription row = saved();
        assertThat(row).isSameAs(keptByAnother);
        assertThat(row.getUserId()).isEqualTo(userId);
        assertThat(row.getP256dh()).isEqualTo(P256DH);
        assertThat(row.getAuth()).isEqualTo(AUTH);
        assertThat(row.getLabel()).isNull();
        verify(repository, never()).countByUserId(any());
    }

    @Test
    void anAccountKeepsAtMostTenBrowsers() {
        when(repository.findByEndpointUrl(ENDPOINT)).thenReturn(Optional.empty());
        when(repository.countByUserId(userId))
                .thenReturn((long) PushSubscriptionService.MAX_SUBSCRIPTIONS_PER_USER);

        assertThatThrownBy(() -> service.register(userId, request(ENDPOINT, P256DH, AUTH, null)))
                .isInstanceOfSatisfying(ApiException.class, e ->
                        assertThat(e.code()).isEqualTo(ApiErrorCode.PUSH_SUBSCRIPTION_LIMIT_REACHED));
        verify(repository, never()).save(any(PushSubscription.class));
    }

    @Test
    void theCapDoesNotRefuseARegistrationAlreadyKept() {
        PushSubscription kept = new PushSubscription();
        kept.setUserId(userId);
        kept.setEndpointUrl(ENDPOINT);
        when(repository.findByEndpointUrl(ENDPOINT)).thenReturn(Optional.of(kept));
        when(repository.countByUserId(userId))
                .thenReturn((long) PushSubscriptionService.MAX_SUBSCRIPTIONS_PER_USER);

        assertThat(service.register(userId, request(ENDPOINT, P256DH, AUTH, null)).endpoint())
                .isEqualTo(ENDPOINT);
    }

    @Test
    void anEndpointTheServiceCannotWakeIsRefused() {
        for (String endpoint : new String[] {
                "http://push.example.invalid/send/abc",
                "https:///send/abc",
                "https://user:secret@push.example.invalid/send/abc",
                "https://push.example.invalid/send/abc#fragment",
                "push.example.invalid/send/abc",
                "https://push.example.invalid/" + "a".repeat(2100)}) {
            assertThatThrownBy(() -> service.register(userId, request(endpoint, P256DH, AUTH, null)))
                    .as(endpoint)
                    .isInstanceOfSatisfying(ApiException.class, e ->
                            assertThat(e.code()).isEqualTo(ApiErrorCode.PUSH_SUBSCRIPTION_INVALID));
        }
        verify(repository, never()).save(any(PushSubscription.class));
    }

    @Test
    void aKeyThatIsNotBase64urlIsRefused() {
        for (String[] pair : new String[][] {
                {P256DH, "too-short"},
                {P256DH, "A".repeat(21) + "="},
                {P256DH, "A".repeat(20) + " " + "A".repeat(5)},
                {"B".repeat(20), AUTH},
                {"B".repeat(161), AUTH}}) {
            assertThatThrownBy(() -> service.register(userId, request(ENDPOINT, pair[0], pair[1], null)))
                    .as("p256dh=%s auth=%s", pair[0], pair[1])
                    .isInstanceOfSatisfying(ApiException.class, e ->
                            assertThat(e.code()).isEqualTo(ApiErrorCode.PUSH_SUBSCRIPTION_INVALID));
        }
        verify(repository, never()).save(any(PushSubscription.class));
    }

    @Test
    void forgettingAnotherAccountsRegistrationIsANotFound() {
        when(repository.findByIdAndUserId(any(), any())).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.delete(userId, UUID.randomUUID()))
                .isInstanceOfSatisfying(ApiException.class, e ->
                        assertThat(e.code()).isEqualTo(ApiErrorCode.PUSH_SUBSCRIPTION_NOT_FOUND));
    }

    @Test
    void forgettingEveryBrowserStaysInsideTheCaller() {
        service.deleteAll(userId);

        verify(repository).deleteByUserId(userId);
    }
}
