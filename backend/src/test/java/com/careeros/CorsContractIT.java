package com.careeros;

import static org.hamcrest.Matchers.allOf;
import static org.hamcrest.Matchers.containsString;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.options;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;

/**
 * The API's cross-origin door.
 *
 * The browser talks to this service from another origin, so the shell's first
 * request on every page is a preflight, and the answer to that preflight is
 * what decides whether the shell can talk to the API at all. The allow-list is
 * configuration (`APP_CORS_ORIGINS`, default `http://localhost:3000`), but
 * until this file nothing had ever driven the door through the real chain: a
 * chain that forgot `.cors(...)`, a method dropped from the list, or a header
 * the shell sends but the door no longer names would have shown up only in a
 * browser, and only as a request that never left.
 *
 * <p>`localhost:3000` is the shipped default in `application.yml`, so that is
 * the shell these tests speak as. The foreign origin stands in for every page
 * on the open internet; it must get the same answer the shell would get if it
 * were not on the list -- a refusal, and no header telling the browser the door
 * was opened.
 */
class CorsContractIT extends AbstractIntegrationTest {

    private static final String SHELL = "http://localhost:3000";
    private static final String FOREIGN = "https://evil.example";

    @Test
    void theShellsPreflightIsAnsweredWithTheWordsTheShellSends() throws Exception {
        mvc.perform(options("/api/v1/auth/login")
                        .header(HttpHeaders.ORIGIN, SHELL)
                        .header(HttpHeaders.ACCESS_CONTROL_REQUEST_METHOD, "POST")
                        .header(HttpHeaders.ACCESS_CONTROL_REQUEST_HEADERS, "authorization, content-type")
                        .header("X-Forwarded-For", "10.88.0.1"))
                .andExpect(status().isOk())
                .andExpect(header().string(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN, SHELL))
                .andExpect(header().string(HttpHeaders.ACCESS_CONTROL_ALLOW_METHODS, containsString("POST")))
                .andExpect(header().string(HttpHeaders.ACCESS_CONTROL_ALLOW_HEADERS, allOf(
                        containsString("authorization"), containsString("content-type"))))
                .andExpect(header().string(HttpHeaders.ACCESS_CONTROL_MAX_AGE, "3600"));
    }

    @Test
    void theShellsActualRequestCarriesTheOriginBack() throws Exception {
        mvc.perform(get("/api/v1/health")
                        .header(HttpHeaders.ORIGIN, SHELL)
                        .header("X-Forwarded-For", "10.88.0.2"))
                .andExpect(status().isOk())
                .andExpect(header().string(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN, SHELL));
    }

    @Test
    void aForeignPreflightDoesNotGetTheDoor() throws Exception {
        mvc.perform(options("/api/v1/auth/login")
                        .header(HttpHeaders.ORIGIN, FOREIGN)
                        .header(HttpHeaders.ACCESS_CONTROL_REQUEST_METHOD, "POST")
                        .header("X-Forwarded-For", "10.88.0.3"))
                .andExpect(status().isForbidden())
                .andExpect(header().doesNotExist(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN));
    }

    @Test
    void aForeignRequestIsRefusedBeforeItReachesTheRoute() throws Exception {
        // `/health` is public: the only thing that can refuse this request is the
        // origin check, so a 403 here says the door is the thing doing the refusing.
        mvc.perform(get("/api/v1/health")
                        .header(HttpHeaders.ORIGIN, FOREIGN)
                        .header("X-Forwarded-For", "10.88.0.4"))
                .andExpect(status().isForbidden())
                .andExpect(header().doesNotExist(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN));
    }

    @Test
    void aMethodTheShellNeverSendsIsNotOnTheDoor() throws Exception {
        mvc.perform(options("/api/v1/auth/login")
                        .header(HttpHeaders.ORIGIN, SHELL)
                        .header(HttpHeaders.ACCESS_CONTROL_REQUEST_METHOD, "TRACE")
                        .header("X-Forwarded-For", "10.88.0.5"))
                .andExpect(status().isForbidden())
                .andExpect(header().doesNotExist(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN));
    }
}
