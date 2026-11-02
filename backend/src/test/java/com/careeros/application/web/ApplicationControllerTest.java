package com.careeros.application.web;

import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.careeros.application.dto.ApplicationDtos.ApplicationPacket;
import com.careeros.application.dto.ApplicationDtos.PacketResume;
import com.careeros.application.service.ApplicationLetterService;
import com.careeros.application.service.ApplicationPacketService;
import com.careeros.application.service.ApplicationService;
import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUserArgumentResolver;
import com.careeros.common.EnvelopeAdvice;
import com.careeros.common.GlobalExceptionHandler;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

/** The packet route is the detail dialog's read, and it is scoped by the session's user. */
class ApplicationControllerTest {

    private static final String USER = "6b0178a0-d352-09c3-ea65-8f107bd28d01";
    private static final UUID APP = UUID.fromString("00000000-0000-0000-0000-0000000000aa");

    private ApplicationPacketService packets;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        packets = mock(ApplicationPacketService.class);
        mvc = MockMvcBuilders.standaloneSetup(
                        new ApplicationController(mock(ApplicationService.class), packets,
                                mock(ApplicationLetterService.class)))
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
    void thePacketIsReadForTheSessionUserAndWrappedOnce() throws Exception {
        when(packets.packet(UUID.fromString(USER), APP)).thenReturn(new ApplicationPacket(
                APP, true,
                new PacketResume(UUID.randomUUID(), UUID.randomUUID(), "Ada CV",
                        "tailored", "tailored", OffsetDateTime.parse("2026-10-01T09:00:00Z")),
                false, null, false, null));

        mvc.perform(get("/api/v1/applications/" + APP + "/packet"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.applicationId").value(APP.toString()))
                .andExpect(jsonPath("$.data.resumeLinked").value(true))
                .andExpect(jsonPath("$.data.resume.title").value("Ada CV"))
                .andExpect(jsonPath("$.data.jdLinked").value(false))
                .andExpect(jsonPath("$.data.jd").doesNotExist());
    }
}
