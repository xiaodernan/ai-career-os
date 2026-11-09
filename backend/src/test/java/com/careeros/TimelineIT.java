package com.careeros;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MvcResult;

/**
 * The timeline bridge, against the live read path (Epic 81).
 *
 * <p>The engine is the ai-service's deterministic fold, so what this IT measures is the
 * bridge the engine depends on: the real rows this account owns travel across as events,
 * the order the engine returns is the order the route forwards, and one reader's rows are
 * not another reader's fuel. The fake's fold is the same shape as the engine's for the
 * well-formed ISO timestamps the bridge writes, so an order assertion here is honest.
 */
class TimelineIT extends ApiIntegrationTest {

    protected static final ObjectMapper MAPPER = new ObjectMapper();

    private String postJson(String auth, String path, Object body) throws Exception {
        MvcResult result = mvc.perform(post(path).header("Authorization", auth)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(body)))
                .andExpect(status().isCreated())
                .andReturn();
        return result.getResponse().getContentAsString();
    }

    private JsonNode timeline(String auth) throws Exception {
        String body = mvc.perform(get("/api/v1/timeline").header("Authorization", auth))
                .andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString();
        return MAPPER.readTree(body).path("data").path("timeline");
    }

    private List<String> when(JsonNode events) {
        List<String> out = new ArrayList<>();
        events.forEach(e -> out.add(e.path("kind").asText()));
        return out;
    }

    @Test
    @DisplayName("an account that has not started answers an honest empty timeline")
    void anEmptyAccountAnswersAnEmptyTimeline() throws Exception {
        String auth = "Bearer " + register("timeline-empty-" + UUID.randomUUID() + "@example.com");

        JsonNode events = timeline(auth);

        assertTrue(events.isArray(), "the timeline must be a list");
        assertEquals(0, events.size(), "an untouched workspace is empty, not broken");
        assertTrue(ai.calls.contains("careerTimeline"),
                "the bridge must be the route's only AI seam");
    }

    @Test
    @DisplayName("the reader's own rows become the timeline, in one ordered answer")
    void theReadersRowsBecomeTheTimeline() throws Exception {
        String auth = "Bearer " + register("timeline-rows-" + UUID.randomUUID() + "@example.com");
        String token = "tl" + UUID.randomUUID().toString().replace("-", "").substring(0, 10);

        Map<String, Object> contact = new LinkedHashMap<>();
        contact.put("name", "Ada Timeline");
        contact.put("relation", "referrer");
        postJson(auth, "/api/v1/contacts", contact);

        Map<String, Object> note = new LinkedHashMap<>();
        note.put("title", "Follow-up plan");
        note.put("content", "Send the referral ask before the weekend.");
        note.put("tags", List.of("networking"));
        postJson(auth, "/api/v1/knowledge/notes", note);

        Map<String, Object> application = new LinkedHashMap<>();
        application.put("title", token + " Backend Engineer");
        application.put("company_name", token + " Robotics");
        application.put("status", "applied");
        postJson(auth, "/api/v1/applications", application);

        JsonNode events = timeline(auth);

        // The three kinds this account owns ride to the reader; the engine's empty kinds do not invent rows.
        List<String> kinds = when(events);
        assertTrue(kinds.contains("contact"), "the contact never reached the timeline: " + kinds);
        assertTrue(kinds.contains("note"), "the note never reached the timeline: " + kinds);
        assertTrue(kinds.contains("application"), "the application never reached the timeline: " + kinds);
        // Deterministic order: at ascending, engine's own tie-break is (at, kind, refId).
        List<String> stamps = new ArrayList<>();
        events.forEach(e -> stamps.add(e.path("at").asText()));
        List<String> sorted = new ArrayList<>(stamps);
        sorted.sort(String::compareTo);
        assertEquals(sorted, stamps,
                "the engine is asked to partition, and this reader's rows came back in anything but order");
        // Every event carries the engine's five fields, none invented.
        events.forEach(e -> {
            assertTrue(e.hasNonNull("at"), "at missing: " + e);
            assertTrue(e.hasNonNull("kind"), "kind missing: " + e);
            assertTrue(e.hasNonNull("refId"), "refId missing: " + e);
            assertTrue(e.hasNonNull("title"), "title missing: " + e);
            assertTrue(e.hasNonNull("summary"), "summary missing: " + e);
        });
        assertTrue(ai.calls.contains("careerTimeline"),
                "the bridge must be the route's only AI seam");
    }

    @Test
    @DisplayName("one reader's rows never reach another reader's timeline")
    void strangersRowsStayOut() throws Exception {
        String ada = "Bearer " + register("timeline-ada-" + UUID.randomUUID() + "@example.com");
        String bob = "Bearer " + register("timeline-bob-" + UUID.randomUUID() + "@example.com");
        String token = "se" + UUID.randomUUID().toString().replace("-", "").substring(0, 10);

        Map<String, Object> note = new LinkedHashMap<>();
        note.put("title", token + " Ada's private scratch");
        note.put("content", "Do not talk about this in the shared roadmap.");
        postJson(ada, "/api/v1/knowledge/notes", note);

        JsonNode bobs = timeline(bob);
        List<String> bobKinds = when(bobs);
        assertTrue(!bobKinds.contains("note"),
                "Ada's row reached Bob's timeline: " + bobs);

        // Ada still sees her own row; the reader scope is what the bridge does, not a filter that erased it.
        Map<String, Object> bobRow = new LinkedHashMap<>();
        bobRow.put("name", "bob-" + token);
        bobRow.put("relation", "peer");
        postJson(bob, "/api/v1/contacts", bobRow);
        JsonNode adas = timeline(ada);
        List<String> adaTitles = new ArrayList<>();
        adas.forEach(e -> adaTitles.add(e.path("title").asText() + " " + e.path("summary").asText()
                + " " + e.path("refId").asText()));
        assertTrue(adaTitles.stream().noneMatch(t -> t.contains("bob-" + token)),
                "Bob's contact leaked into Ada's timeline: " + adaTitles);
        assertEquals(1, adas.size(), "Ada sees exactly her own row, nothing else: " + adas);
        assertEquals("note", adas.get(0).path("kind").asText(),
                "Ada's timeline lost its note in transit");
    }
}
