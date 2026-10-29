package com.careeros;

import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.matchesPattern;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.careeros.common.RequestIdFilter;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.web.servlet.MockMvc;

/**
 * The filter sits outside the security chain, so the refusals that arrive without a
 * session -- the ones an operator is most often asked about -- carry the id too.
 */
class RequestIdIT extends AbstractIntegrationTest {

    private static final String UUID = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}";

    @Autowired
    private MockMvc mvc;

    @Test
    void anUnauthenticatedRefusalCarriesAnId() throws Exception {
        mvc.perform(get("/api/v1/me"))
                .andExpect(status().isUnauthorized())
                .andExpect(header().string(RequestIdFilter.HEADER, matchesPattern(UUID)));
    }

    @Test
    void aProxyIdIsEchoedAndReadableByTheBrowser() throws Exception {
        mvc.perform(get("/api/v1/me")
                        .header(RequestIdFilter.HEADER, "edge-7c1d4f9a")
                        .header("Origin", "http://localhost:3000"))
                .andExpect(status().isUnauthorized())
                .andExpect(header().string(RequestIdFilter.HEADER, "edge-7c1d4f9a"))
                .andExpect(header().string("Access-Control-Expose-Headers",
                        containsString(RequestIdFilter.HEADER)));
    }

    @Test
    void aMalformedIdIsReplacedRatherThanRefused() throws Exception {
        mvc.perform(get("/api/v1/me").header(RequestIdFilter.HEADER, "bad id"))
                .andExpect(status().isUnauthorized())
                .andExpect(header().string(RequestIdFilter.HEADER, matchesPattern(UUID)));
    }
}
