package com.careeros.ai.web;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.careeros.ai.dto.OfferDtos.CompareOffersRequest;
import com.careeros.ai.dto.OfferDtos.SalaryRequest;
import com.careeros.ai.service.OfferService;
import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUserArgumentResolver;
import com.careeros.common.EnvelopeAdvice;
import com.careeros.common.GlobalExceptionHandler;
import java.util.List;
import java.util.Map;
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
 * The salary & offer routes (Epics 12.1-12.5).
 *
 * <p>The engines own the numbers; what this pins is the pass-through. The
 * comparison route is the interesting one: its body carries a list of offers,
 * and a list is where a field name is easiest to get wrong — so the offer's
 * grant has to arrive as a nested object with the engine's own field names,
 * and the ranking stays the engine's to compute.
 */
class OfferControllerTest {

    private static final String USER = "6b0178a0-d352-09c3-ea65-8f107bd28d01";

    private OfferService offers;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        offers = mock(OfferService.class);
        OfferController controller = new OfferController(offers);
        mvc = MockMvcBuilders.standaloneSetup(controller)
                .setControllerAdvice(new EnvelopeAdvice(), new GlobalExceptionHandler())
                .setCustomArgumentResolvers(new CurrentUserArgumentResolver())
                .build();
        SecurityContextHolder.getContext().setAuthentication(new UsernamePasswordAuthenticationToken(
                new AuthUser(UUID.fromString(USER), "ada@example.invalid", "user"), null, List.of()));
    }

    @AfterEach
    void tearDown() {
        SecurityContextHolder.clearContext();
    }

    @Test
    void the_benchmark_is_the_engines_answer_wrapped_once() throws Exception {
        when(offers.salaryBenchmark(eq(UUID.fromString(USER)), any(SalaryRequest.class)))
                .thenReturn(Map.of("percentiles", Map.of("p50", 420000), "sampleSize", 8));

        mvc.perform(post("/api/v1/offers/salary-benchmark")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"role\":\"Backend Engineer\",\"location\":\"Shanghai\",\"currency\":\"CNY\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.percentiles.p50").value(420000))
                .andExpect(jsonPath("$.data.sampleSize").value(8));

        ArgumentCaptor<SalaryRequest> sent = ArgumentCaptor.forClass(SalaryRequest.class);
        verify(offers).salaryBenchmark(eq(UUID.fromString(USER)), sent.capture());
        assertThat(sent.getValue().role()).isEqualTo("Backend Engineer");
        assertThat(sent.getValue().location()).isEqualTo("Shanghai");
        // The caller named no target salary; the bridge must not manufacture one.
        assertThat(sent.getValue().targetSalary()).isNull();
    }

    @Test
    void an_offer_without_a_role_is_refused_before_the_call() throws Exception {
        mvc.perform(post("/api/v1/offers/salary-benchmark")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"location\":\"Shanghai\"}"))
                .andExpect(status().isBadRequest());

        verifyNoInteractions(offers);
    }

    /**
     * The comparison route's list of offers is the part a field name is easiest
     * to get wrong: the grant has to arrive as a nested object, and the offer's
     * own four fields have to survive the trip.
     */
    @Test
    void the_comparison_carries_every_offer_with_its_grant() throws Exception {
        when(offers.compareOffers(eq(UUID.fromString(USER)), any(CompareOffersRequest.class)))
                .thenReturn(Map.of("rows", List.of(Map.of("label", "Offer A", "totalComp", 520000))));

        mvc.perform(post("/api/v1/offers/compare")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"role":"Backend Engineer","matchScore":0.82,
                                 "offers":[{"label":"Offer A","base":500000,"bonus":20000,
                                            "equity":{"shares":1000,"strikePrice":10,
                                                      "currentPrice":40,"vestYears":4}}]}
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.rows[0].label").value("Offer A"));

        ArgumentCaptor<CompareOffersRequest> sent = ArgumentCaptor.forClass(CompareOffersRequest.class);
        verify(offers).compareOffers(eq(UUID.fromString(USER)), sent.capture());
        assertThat(sent.getValue().offers()).hasSize(1);
        assertThat(sent.getValue().offers().get(0).label()).isEqualTo("Offer A");
        assertThat(sent.getValue().offers().get(0).base()).isEqualTo(500000);
        assertThat(sent.getValue().offers().get(0).bonus()).isEqualTo(20000);
        assertThat(sent.getValue().offers().get(0).equity()).isNotNull();
        assertThat(sent.getValue().offers().get(0).equity().shares()).isEqualTo(1000);
        assertThat(sent.getValue().offers().get(0).equity().vestYears()).isEqualTo(4);
        assertThat(sent.getValue().matchScore()).isEqualTo(0.82);
    }

    @Test
    void a_comparison_with_no_offers_is_refused_before_the_call() throws Exception {
        mvc.perform(post("/api/v1/offers/compare")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"role\":\"Backend Engineer\",\"offers\":[]}"))
                .andExpect(status().isBadRequest());

        verifyNoInteractions(offers);
    }

    @Test
    void an_unauthenticated_call_is_refused_by_the_framework_not_the_client() throws Exception {
        SecurityContextHolder.clearContext();
        mvc.perform(post("/api/v1/offers/negotiate")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"role\":\"Backend Engineer\",\"offerBase\":400000}"))
                .andExpect(status().isUnauthorized());
    }
}
