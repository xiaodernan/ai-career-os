package com.careeros;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.web.servlet.MvcResult;

/**
 * A saved search's voice, against the schema Flyway builds (roadmap 29.1).
 *
 * <p>The matcher's unit tests read the filters it asks for; only a database can say the board's
 * SQL answers them. Two matching postings are created through the real job flow -- one still
 * inside the seven-day news window, one pushed twenty days back while the search itself is
 * thirty days old -- and the inbox has to announce exactly the recent one. A dropped predicate,
 * a window computed from the wrong clock or a {@code posted_at} join that never bounds would
 * each pass the mocks and fail here.
 *
 * <p>The second test is the episode's promise end to end: dismissing the item silences that
 * posting, and the next posting to match arrives as a fresh unread item -- nothing but the
 * arrival itself is stored to make that true.
 */
class SavedSearchAlertIT extends ApiIntegrationTest {

    @Autowired
    private JdbcTemplate jdbc;

    private String createJob(String auth, String title) throws Exception {
        Map<String, Object> request = new LinkedHashMap<>();
        request.put("title", title);
        request.put("company", Map.of("name", "AlertCo " + title));
        request.put("location", "Hangzhou");
        request.put("description", "We are hiring for " + title + ".");
        MvcResult created = mvc.perform(post("/api/v1/jobs")
                        .header("Authorization", "Bearer " + auth)
                        .contentType(MediaType.APPLICATION_JSON).content(json(request)))
                .andReturn();
        if (created.getResponse().getStatus() != 201) {
            throw new IllegalStateException("job create answered " + created.getResponse().getStatus()
                    + ": " + created.getResponse().getContentAsString());
        }
        return MAPPER.readTree(created.getResponse().getContentAsString())
                .path("data").path("id").asText();
    }

    private String createSearch(String auth, String name, String q) throws Exception {
        MvcResult created = mvc.perform(post("/api/v1/saved-searches")
                        .header("Authorization", "Bearer " + auth)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(Map.of("name", name, "criteria", Map.of("q", q)))))
                .andExpect(status().isCreated())
                .andReturn();
        return MAPPER.readTree(created.getResponse().getContentAsString())
                .path("data").path("id").asText();
    }

    private JsonNode inbox(String auth) throws Exception {
        MvcResult result = mvc.perform(get("/api/v1/notifications")
                        .header("Authorization", "Bearer " + auth))
                .andExpect(status().isOk())
                .andReturn();
        return MAPPER.readTree(result.getResponse().getContentAsString()).path("data");
    }

    private static JsonNode savedSearchItem(JsonNode inbox) {
        for (JsonNode item : inbox.path("items")) {
            if ("saved_search".equals(item.path("kind").asText())) {
                return item;
            }
        }
        return null;
    }

    private static String needle() {
        return "qx" + Long.toString(Math.abs(UUID.randomUUID().getMostSignificantBits()), 36);
    }

    @Test
    @DisplayName("only a matching posting inside the news window is announced, with its count and link")
    void theSearchSpeaksAboutThePostingThatIsStillNews() throws Exception {
        String auth = register("alert-" + UUID.randomUUID() + "@example.com");
        String needle = needle();
        String searchName = "Roles for " + needle;
        String searchId = createSearch(auth, searchName, needle);

        createJob(auth, "Backend Engineer " + needle);
        String old = createJob(auth, "Platform Engineer " + needle);

        // The search is older than the news window, so its own creation is not the start;
        // the old posting falls outside the seven-day floor and must not be counted.
        jdbc.update("update saved_searches set created_at = now() - interval '10 days'"
                + " where id = ?", UUID.fromString(searchId));
        jdbc.update("update jobs set posted_at = now() - interval '20 days' where id = ?",
                UUID.fromString(old));

        JsonNode data = inbox(auth);
        JsonNode item = savedSearchItem(data);

        assertNotNull(item, "the inbox announced no saved search: " + data);
        assertEquals(searchName, item.path("title").asText());
        assertEquals(1, item.path("count").asInt(),
                "the posting outside the news window was counted: " + item);
        assertTrue(item.path("link").asText().startsWith("/jobs?q=" + needle),
                "the link does not open the board on the same question: " + item);
        assertFalse(item.path("read").asBoolean());
        assertTrue(item.path("key").asText().startsWith("saved_search:" + searchId + ":"),
                "the episode is not keyed by the search and its newest arrival: " + item);
    }

    @Test
    @DisplayName("a dismissed alert is silenced until a newer posting matches")
    void aDismissedAlertReturnsForANewArrival() throws Exception {
        String auth = register("alert-" + UUID.randomUUID() + "@example.com");
        String needle = needle();
        String searchId = createSearch(auth, "Roles for " + needle, needle);
        String first = createJob(auth, "Data Engineer " + needle);
        // Both clocks are moved back explicitly: the search existed before its first match, and
        // that posting is ten seconds older than the next, so the two are distinct episodes --
        // the key carries epoch seconds, and two writes in one second are one episode by design.
        jdbc.update("update saved_searches set created_at = now() - interval '1 hour' where id = ?",
                UUID.fromString(searchId));
        jdbc.update("update jobs set posted_at = now() - interval '10 seconds' where id = ?",
                UUID.fromString(first));

        JsonNode item = savedSearchItem(inbox(auth));
        assertNotNull(item, "the first matching posting was never announced");
        String key = item.path("key").asText();

        mvc.perform(post("/api/v1/notifications/dismiss")
                        .header("Authorization", "Bearer " + auth)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(Map.of("key", key))))
                .andExpect(status().isOk());

        assertEquals(null, savedSearchItem(inbox(auth)),
                "the dismissed episode is still in the inbox");

        createJob(auth, "SRE " + needle);
        JsonNode fresh = savedSearchItem(inbox(auth));

        assertNotNull(fresh, "a newer matching posting did not raise a new item");
        assertFalse(fresh.path("key").asText().equals(key));
        assertFalse(fresh.path("read").asBoolean());
    }
}
