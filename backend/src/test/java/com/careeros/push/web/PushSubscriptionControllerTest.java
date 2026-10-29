package com.careeros.push.web;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUserArgumentResolver;
import com.careeros.common.EnvelopeAdvice;
import com.careeros.common.GlobalExceptionHandler;
import com.careeros.push.entity.PushSubscription;
import com.careeros.push.repository.PushSubscriptionRepository;
import com.careeros.push.service.PushSubscriptionService;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.http.MediaType;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

/**
 * The push-subscription routes (roadmap 33.1).
 *
 * <p>Two claims are worth a route-level test. Ownership: every query is anchored on the
 * caller, so one account's browsers are never another's to list, re-point or forget. And the
 * refusals: an address this service cannot wake, or an eleventh browser, answers with the
 * code the settings switch acts on rather than a generic validation failure.
 */
class PushSubscriptionControllerTest {

    private static final UUID ALICE = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final UUID KEPT = UUID.fromString("44444444-4444-4444-8444-444444444444");
    private static final String ENDPOINT = "https://push.example.invalid/send/abc123";
    private static final String P256DH = "B".repeat(87);
    private static final String AUTH = "A".repeat(22);

    private PushSubscriptionRepository repository;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        repository = mock(PushSubscriptionRepository.class);
        mvc = MockMvcBuilders.standaloneSetup(
                        new PushSubscriptionController(new PushSubscriptionService(repository)))
                .setControllerAdvice(new EnvelopeAdvice(), new GlobalExceptionHandler())
                .setCustomArgumentResolvers(new CurrentUserArgumentResolver())
                .build();
        SecurityContextHolder.getContext().setAuthentication(new UsernamePasswordAuthenticationToken(
                new AuthUser(ALICE, "ada@example.invalid", "user"), null, List.of()));
        when(repository.save(any(PushSubscription.class))).thenAnswer(i -> i.getArgument(0));
    }

    @AfterEach
    void tearDown() {
        SecurityContextHolder.clearContext();
    }

    private static String body(String endpoint) {
        return """
                {"endpoint":"%s","p256dh":"%s","auth":"%s","label":"Work laptop"}
                """.formatted(endpoint, P256DH, AUTH);
    }

    @Test
    void registeringStoresUnderTheCallerAndAnswersTheKeptRow() throws Exception {
        mvc.perform(post("/api/v1/push/subscriptions")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body("  " + ENDPOINT + "  ")))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.endpoint").value(ENDPOINT))
                .andExpect(jsonPath("$.data.label").value("Work laptop"));

        ArgumentCaptor<PushSubscription> cap = ArgumentCaptor.forClass(PushSubscription.class);
        verify(repository).save(cap.capture());
        assertThat(cap.getValue().getUserId()).isEqualTo(ALICE);
        assertThat(cap.getValue().getEndpointUrl()).isEqualTo(ENDPOINT);
    }

    @Test
    void theListIsTheCallersOwnWithTheEndpointAndLabel() throws Exception {
        PushSubscription first = new PushSubscription();
        first.setUserId(ALICE);
        first.setEndpointUrl(ENDPOINT);
        first.setLabel("Work laptop");
        PushSubscription second = new PushSubscription();
        second.setUserId(ALICE);
        second.setEndpointUrl("https://push.example.invalid/send/def456");
        second.setLabel("Phone");
        when(repository.findByUserIdOrderByCreatedAtDesc(ALICE)).thenReturn(List.of(first, second));

        mvc.perform(get("/api/v1/push/subscriptions"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data[0].endpoint").value(ENDPOINT))
                .andExpect(jsonPath("$.data[0].label").value("Work laptop"))
                .andExpect(jsonPath("$.data[1].label").value("Phone"));

        verify(repository).findByUserIdOrderByCreatedAtDesc(ALICE);
    }

    @Test
    void forgettingAnotherAccountsRegistrationIsA404NamingTheCode() throws Exception {
        when(repository.findByIdAndUserId(KEPT, ALICE)).thenReturn(Optional.empty());

        mvc.perform(delete("/api/v1/push/subscriptions/{id}", KEPT))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error.code").value("PUSH_SUBSCRIPTION_NOT_FOUND"));
    }

    @Test
    void forgettingAnOwnedRegistrationIsA204() throws Exception {
        PushSubscription row = new PushSubscription();
        row.setUserId(ALICE);
        when(repository.findByIdAndUserId(KEPT, ALICE)).thenReturn(Optional.of(row));

        mvc.perform(delete("/api/v1/push/subscriptions/{id}", KEPT))
                .andExpect(status().isNoContent());

        verify(repository).delete(row);
    }

    @Test
    void forgettingEveryBrowserStaysInsideTheCaller() throws Exception {
        mvc.perform(delete("/api/v1/push/subscriptions"))
                .andExpect(status().isNoContent());

        verify(repository).deleteByUserId(ALICE);
    }

    @Test
    void anAddressTheServiceCannotWakeIsRefusedWithItsOwnCode() throws Exception {
        mvc.perform(post("/api/v1/push/subscriptions")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body("http://push.example.invalid/send/abc")))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("PUSH_SUBSCRIPTION_INVALID"));
    }

    @Test
    void anEleventhBrowserIsRefusedWithItsOwnCode() throws Exception {
        when(repository.findByEndpointUrl(ENDPOINT)).thenReturn(Optional.empty());
        when(repository.countByUserId(ALICE)).thenReturn(10L);

        mvc.perform(post("/api/v1/push/subscriptions")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body(ENDPOINT)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("PUSH_SUBSCRIPTION_LIMIT_REACHED"));
    }

    @Test
    void aBlankEndpointIsABeanValidationFailure() throws Exception {
        mvc.perform(post("/api/v1/push/subscriptions")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body("  ")))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("VALIDATION_FAILED"));
    }

}
