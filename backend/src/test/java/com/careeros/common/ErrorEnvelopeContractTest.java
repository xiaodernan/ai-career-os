package com.careeros.common;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Positive;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

/**
 * The error envelope's details channel — the shape under `error.details` that the
 * frontend's {@code ApiError} carries into the forms.
 *
 * The census (ApiErrorCodeCensusTest) pinned the codes and their statuses; this file
 * pins what travels *beside* them. Details are produced in exactly one live place —
 * the validation handler — and were only ever spot-checked for `details[0].field`.
 * Unpinned until now: that every error envelope carries `details` at all (the
 * frontend reads the property unconditionally), that a validation detail carries
 * `message` and `rejectedValue` next to `field`, and that `rejectedValue` is the
 * client's own submitted bytes echoed back — a fact worth a test, because one day
 * somebody will point this pipeline at a field whose value must not be echoed.
 */
class ErrorEnvelopeContractTest {

    record NameForm(@NotBlank String name, @Positive int count) {
    }

    @RestController
    static class Routes {
        @PostMapping("/validate")
        String validate(@RequestBody @Valid NameForm form) {
            return form.name();
        }

        @GetMapping("/domain")
        String domain() {
            throw new ApiException(ApiErrorCode.INVALID_STATUS, "Unknown application status: xyz",
                    List.of(Map.of("status", "xyz", "allowed", List.of("saved", "applied"))));
        }
    }

    private final MockMvc mvc = MockMvcBuilders.standaloneSetup(new Routes())
            .setControllerAdvice(new EnvelopeAdvice(), new GlobalExceptionHandler())
            .build();

    @Test
    void a_validation_error_carries_field_message_and_the_submitted_value() throws Exception {
        mvc.perform(post("/validate").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"name\":\"\",\"count\":3}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("VALIDATION_FAILED"))
                .andExpect(jsonPath("$.error.details[0].field").value("name"))
                .andExpect(jsonPath("$.error.details[0].message").exists())
                // rejectedValue is the client's own value echoed back, not a correction.
                .andExpect(jsonPath("$.error.details[0].rejectedValue").value(""));
    }

    @Test
    void every_field_of_the_form_gets_its_own_detail_entry() throws Exception {
        mvc.perform(post("/validate").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"name\":\"   \",\"count\":-2}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.details.length()").value(2))
                .andExpect(jsonPath("$.error.details[?(@.field == 'name')]").exists())
                .andExpect(jsonPath("$.error.details[?(@.field == 'count')]").exists());
    }

    @Test
    void a_domain_exception_carrying_details_reaches_the_wire_intact() throws Exception {
        mvc.perform(get("/domain"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("INVALID_STATUS"))
                .andExpect(jsonPath("$.error.message").value("Unknown application status: xyz"))
                .andExpect(jsonPath("$.error.details[0].status").value("xyz"))
                .andExpect(jsonPath("$.error.details[0].allowed[1]").value("applied"));
    }

    @Test
    void every_error_envelope_carries_a_details_array_even_when_empty() throws Exception {
        // ApiResponse is @JsonInclude(ALWAYS) and every handler builds details through
        // ApiError.of, so the property is always present — the frontend reads it without
        // a guard, and an omitted key would read as undefined where a list is expected.
        for (ApiErrorCode code : ApiErrorCode.values()) {
            var body = com.fasterxml.jackson.databind.json.JsonMapper.builder().build()
                    .writeValueAsString(ApiResponse.error(ApiError.of(code, "m")));
            org.assertj.core.api.Assertions.assertThat(body)
                    .as("%s's envelope must carry details", code)
                    .contains("\"details\":[]");
        }
    }

    @Test
    void the_constructor_defends_the_caller_from_null_and_mutable_details() {
        ApiException ex = new ApiException(ApiErrorCode.VALIDATION_FAILED, "m",
                List.of(Map.of("k", "v")));
        org.assertj.core.api.Assertions.assertThat(ex.details()).containsExactly(Map.of("k", "v"));
        ApiException empty = new ApiException(ApiErrorCode.VALIDATION_FAILED, "m", null);
        org.assertj.core.api.Assertions.assertThat(empty.details()).isEmpty();
        // A copy, not the caller's list: mutation after the throw cannot edit the wire.
        List<Map<String, Object>> caller = new java.util.ArrayList<>(List.of(Map.of("k", "v")));
        ApiException copied = new ApiException(ApiErrorCode.VALIDATION_FAILED, "m", caller);
        caller.clear();
        org.assertj.core.api.Assertions.assertThat(copied.details()).hasSize(1);
    }
}
