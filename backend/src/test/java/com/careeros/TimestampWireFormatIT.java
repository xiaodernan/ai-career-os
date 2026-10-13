package com.careeros;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MvcResult;

/**
 * The one wire-format question no unit test can answer, because no unit test carries the
 * application's ObjectMapper: does an {@code OffsetDateTime} reach the browser as an ISO-8601
 * string or as epoch seconds?
 *
 * The frontend's answer is not negotiable. {@code formatDate} and {@code formatDateTime}
 * (frontend/src/lib/format.ts:3-10) take {@code value?: string | null} and hand it to
 * {@code new Date(value)}: an epoch-seconds number would be read as milliseconds and land in
 * 1970, while a string is fine. So the mapper must disable
 * {@code WRITE_DATES_AS_TIMESTAMPS} — which {@code EnvelopeJson} (the mapper the filters use)
 * already does, explicit, and this test confirms the MVC converter's mapper agrees with it.
 *
 * The value itself is a seeded conversation's createdAt/updatedAt, which also pins that the
 * two timestamps exist on the wire at all: a JSON view that dropped them would make the
 * sidebar's "2 days ago" render blank.
 */
class TimestampWireFormatIT extends ApiIntegrationTest {

    private String authHeader() throws Exception {
        return "Bearer " + register("ts-" + UUID.randomUUID() + "@example.com");
    }

    @Test
    @DisplayName("a timestamp answers an ISO-8601 string, not epoch seconds the browser would misread")
    void timestampsAreIsoStringsOnTheWire() throws Exception {
        String auth = authHeader();
        String convId = createConversation(auth);

        mvc.perform(get("/api/v1/conversations/" + convId).header("Authorization", auth))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.createdAt").isString())
                .andExpect(jsonPath("$.data.createdAt").value(org.hamcrest.Matchers
                        .matchesPattern("\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?Z?")))
                .andExpect(jsonPath("$.data.updatedAt").isString());
    }

    @Test
    @DisplayName("the same hold for the resume-version panel the versions list feeds")
    void versionTimestampsSurviveTheRoundTrip() throws Exception {
        String auth = authHeader();
        // A resume created through the public API carries a version with createdAt.
        MvcResult created = mvc.perform(post("/api/v1/resumes")
                        .header("Authorization", auth)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(Map.of("title", "TS resume",
                                "plaintext", "Backend engineer, Java, Kafka, distributed systems"))))
                .andExpect(status().isCreated()).andReturn();

        JsonNode data = MAPPER.readTree(created.getResponse().getContentAsString()).path("data");
        UUID versionId = UUID.fromString(data.path("currentVersionId").asText());

        mvc.perform(get("/api/v1/resume-versions/" + versionId).header("Authorization", auth))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.createdAt").isString())
                .andExpect(jsonPath("$.data.createdAt").value(org.hamcrest.Matchers
                        .matchesPattern("\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?Z?")));
    }

    private String createConversation(String auth) throws Exception {
        MvcResult chat = mvc.perform(post("/api/v1/copilot/chat")
                        .header("Authorization", auth)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(Map.of("message", "What should I focus on next?"))))
                .andExpect(status().isOk()).andReturn();
        String convId = MAPPER.readTree(chat.getResponse().getContentAsString())
                .path("data").path("conversationId").asText();
        if (convId == null || convId.isBlank()) {
            throw new IllegalStateException("the copilot chat did not name a conversation");
        }
        return convId;
    }
}
