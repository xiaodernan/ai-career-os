package com.careeros.common;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.List;
import java.util.Set;
import java.util.TreeSet;
import java.util.stream.Collectors;
import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * The error-code vocabulary, as a live census.
 *
 * {@link ApiErrorCode} is the machine-readable contract every client reads — the enum's
 * own comment says "never rename an emitted code" — and three properties of it were
 * unpinned. The status map was spot-checked by whatever route happened to throw each
 * code (a dozen of the 90); an unreachable-coded 2xx would make an error invisible to
 * every client's error path and nothing would have noticed. A rename is a wire break
 * nobody can see from the type system. And two of the 90 codes are deliberately
 * unreachable today, which reads as an enum bug to the next session unless it is
 * written down somewhere a test wakes up.
 *
 * The handler's fidelity half of this file matters as much as the shape half: the
 * advice is one line (`status(ex.code().status())`), so this exercises it for all 90
 * codes at once rather than trusting that the twelve spot-checks represent the rest.
 */
class ApiErrorCodeCensusTest {

    /** The route that throws whatever code the census names; see {@link #everyCode()}. */
    @RestController
    static class Thrower {
        @GetMapping("/boom")
        String boom(@RequestParam String code) {
            throw new ApiException(ApiErrorCode.valueOf(code), "census boom");
        }
    }

    private MockMvc mvc() {
        return MockMvcBuilders.standaloneSetup(new Thrower())
                .setControllerAdvice(new GlobalExceptionHandler())
                .build();
    }

    /**
     * Codes registered in the vocabulary with no throw site in the backend today.
     * Pinned by name so the next session reads the reason instead of filing an enum
     * bug — and so whoever builds the missing guard knows the code already exists.
     */
    private static final Set<String> DELIBERATELY_UNREACHABLE = Set.of(
            "INVALID_TRANSITION", // the kanban has no transition graph: applyStatusChange
                                 // allows every legal->legal move, so no move is illegal
            "MATCH_NOT_FOUND");   // the only match route computes one (POST /{id}/match);
                                 // no read path requires an existing row

    @Test
    void everyCodeIsAClientVisibleErrorStatus() {
        for (ApiErrorCode code : ApiErrorCode.values()) {
            int status = code.status().value();
            org.assertj.core.api.Assertions.assertThat(status)
                    .as("%s maps to %d — an error the client cannot see as an error", code, status)
                    .isBetween(400, 599);
        }
    }

    @Test
    void theNameCensusIsFrozenUnlessThisTestIsEditedOnPurpose() {
        // The enum's contract: "never rename an emitted code". A rename breaks the wire
        // for every client, and nothing else in the type system can see it — so the whole
        // name set is the pin. Adding a code means editing this list, deliberately.
        List<String> names = java.util.Arrays.stream(ApiErrorCode.values())
                .map(Enum::name).sorted().toList();
        org.assertj.core.api.Assertions.assertThat(names).containsExactly(
                "AI_SERVICE_BAD_REQUEST", "AI_SERVICE_CONFLICT", "AI_SERVICE_EMPTY_RESPONSE", "AI_SERVICE_NOT_FOUND",
                "AI_SERVICE_UNAVAILABLE", "APPLICATION_NOT_FOUND", "BUNDLE_NOT_PLANNABLE", "BUNDLE_NO_SECTION",
                // 34.1: the calendar feed's token is a second link credential, and its refusal
                // is about a subscription a calendar app keeps polling -- its own sentence.
                "CALENDAR_LINK_INVALID",
                "COMPANY_NOT_FOUND", "CONFIRMATION_MISMATCH", "CONTACT_NOT_FOUND", "CONVERSATION_NOT_FOUND",
                // 30.4: a signed-in reader's mistyped current password is not a failed sign-in,
                // so the four re-authentication sites name this code instead of INVALID_CREDENTIALS.
                "CURRENT_PASSWORD_INCORRECT",
                "DOCUMENT_KEY_NOT_OWNED",
                "DOCUMENT_NOT_FOUND", "EMAIL_ALREADY_REGISTERED", "EMAIL_CHANGE_INVALID", "EMAIL_UNCHANGED",
                "FEED_BOARD_INVALID", "FEED_LIMIT_REACHED",
                "FEED_URL_INVALID",
                "FILE_EMPTY", "FILE_KEY_INVALID",
                "FILE_KEY_MALFORMED", "FILE_TOO_LARGE", "FORBIDDEN",
                // 37.1: a forwarding address refuses a forged token and a missing receiving
                // domain with its own sentences; 37.3 adds the replies page's two refusals --
                // a letter that is not the account's, and one already filed elsewhere.
                "INBOUND_LINK_INVALID", "INBOUND_MAIL_ALREADY_FILED", "INBOUND_MAIL_NOT_FOUND",
                "INBOUND_NOT_CONFIGURED",
                "INGESTION_FEED_NOT_FOUND",
                "INGESTION_RUN_ALREADY_APPLIED", "INGESTION_RUN_NOT_APPLICABLE", "INGESTION_RUN_NOT_FOUND",
                "INTERNAL_ERROR",
                "INTERVIEW_ALREADY_STARTED", "INTERVIEW_NOTHING_TO_FINALIZE", "INTERVIEW_NOT_STARTED", "INTERVIEW_NO_QUESTION",
                "INVALID_CREDENTIALS", "INVALID_FILE_TYPE", "INVALID_STATUS", "INVALID_TRANSITION",
                "JD_NOT_FOUND", "JOB_NOT_FOUND",
                // 30.5: the catch-all had three meanings; the session-row and the mail-link
                // refusals now name their own, so NOT_FOUND is the address and nothing else.
                "LOGIN_SESSION_NOT_FOUND", "MAIL_LINK_INVALID",
                "MALFORMED_REQUEST", "MATCH_NOT_FOUND",
                "METHOD_NOT_ALLOWED",
                // 36.1: a second factor that is already on, an account that never started one, and
                // a code that is not the phone's -- three different answers, so the settings card
                // can tell the reader whether to stop, start, or retype.
                // 36.2: the login's two answers -- a code is needed (the browser shows the field)
                // and a code is wrong (the reader reads the phone again) -- asked only after the
                // password matched, so a stranger never hears either.
                "MFA_ALREADY_ACTIVE", "MFA_CODE_INVALID", "MFA_INVALID", "MFA_NOT_ENROLLED", "MFA_REQUIRED",
                // 20.1: each refusal of a malformed nightly report has one meaning, so each
                // got its own code rather than one code with three sentences.
                "NIGHTLY_REPORT_CLOCK_REVERSED", "NIGHTLY_REPORT_STATUS_INVALID", "NIGHTLY_REPORT_SUMMARY_TOO_LARGE",
                "NOTE_NOT_FOUND", "NOT_FOUND", "PASSWORD_UNCHANGED", "PROFILE_NOT_FOUND",
                // 33.1: a browser registration is refused, capped or forgotten -- each with its
                // own sentence, so the settings switch can tell the reader which happened.
                "PUSH_SUBSCRIPTION_INVALID", "PUSH_SUBSCRIPTION_LIMIT_REACHED",
                "PUSH_SUBSCRIPTION_NOT_FOUND",
                "RATE_LIMITED", "RESET_TOKEN_INVALID", "RESET_TOKEN_OWNER_NOT_FOUND", "RESUME_FILE_MISSING",
                "RESUME_NOT_AVAILABLE", "RESUME_NOT_FOUND", "RESUME_NOT_INGESTED", "RESUME_NOT_PARSED",
                "RESUME_NOT_TAILABLE", "RESUME_TEXT_NOT_READY", "RESUME_VERSION_MISSING", "RUN_NOT_FOUND",
                "SALARY_RANGE_INVALID", "SAVED_SEARCH_EMPTY", "SAVED_SEARCH_LIMIT_REACHED",
                "SAVED_SEARCH_NOT_FOUND", "SESSION_NOT_FOUND",
                "SOURCE_NOT_FOUND", "STORAGE_DELETE_FAILED",
                "STORAGE_PRESIGN_FAILED",
                "STORAGE_READ_FAILED", "STORAGE_WRITE_FAILED", "TAILORED_BODY_MISSING",
                "TOKEN_EXPIRED", "TOKEN_INVALID",
                "TOKEN_MALFORMED", "TOKEN_OWNER_NOT_FOUND", "TOKEN_REUSED", "UNAUTHORIZED",
                "UPLOAD_UNREADABLE", "USER_DISABLED", "USER_NOT_FOUND", "VALIDATION_FAILED",
                "VALIDATION_FIELD_REQUIRED", "VALIDATION_KIND_UNKNOWN", "VERSION_NOT_FOUND",
                "VERSION_NOT_OWNED");
    }

    @Test
    void everyCodeReachesTheWireAsItsDeclaredStatusAndName() throws Exception {
        MockMvc mvc = mvc();
        for (ApiErrorCode code : ApiErrorCode.values()) {
            mvc.perform(get("/boom").param("code", code.name()))
                    .andExpect(status().is(code.status().value()))
                    .andExpect(jsonPath("$.success").value(false))
                    .andExpect(jsonPath("$.error.code").value(code.name()))
                    .andExpect(jsonPath("$.error.message").value("census boom"));
        }
    }

    @Test
    void theDeliberatelyUnreachableCodesStillExistAndTheRestAreReachable() {
        Set<String> names = ApiErrorCode.values().length > 0
                ? java.util.Arrays.stream(ApiErrorCode.values()).map(Enum::name)
                        .collect(Collectors.toCollection(TreeSet::new))
                : Set.of();
        // The vocabulary may only contain reachable codes plus the documented dead ones.
        org.assertj.core.api.Assertions.assertThat(names).containsAll(DELIBERATELY_UNREACHABLE);
        org.assertj.core.api.Assertions.assertThat(DELIBERATELY_UNREACHABLE).allMatch(names::contains);
    }
}
