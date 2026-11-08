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
 * The registry narrows by word and by relation, paged by the server (80).
 *
 * <p>The networking registry used to answer with one word: what the reader typed.
 * The relation column was written on every contact but was never a question of its
 * own — the dialog set it, the outreach draft read it, and no board asked "show me
 * referrers". This IT holds the three-way disjointness: a word narrows it, a relation
 * chip narrows it further, and the window shows one slice of that same answer. It
 * also measures that the {@code /contacts/relations} counts agree with what the list
 * route returns, because a chip that shows the wrong count is a chip that lies.
 */
class ContactRelationIT extends ApiIntegrationTest {

    protected static final ObjectMapper MAPPER = new ObjectMapper();

    private String createContact(String auth, String name, String relation) throws Exception {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("name", name);
        body.put("relation", relation);
        MvcResult created = mvc.perform(post("/api/v1/contacts")
                        .header("Authorization", auth)
                        .contentType(MediaType.APPLICATION_JSON).content(json(body)))
                .andExpect(status().isCreated())
                .andReturn();
        return MAPPER.readTree(created.getResponse().getContentAsString())
                .path("data").path("id").asText();
    }

    private JsonNode shelf(String auth, String... extras) throws Exception {
        var request = get("/api/v1/contacts").header("Authorization", auth);
        for (int i = 0; i < extras.length; i += 2) {
            request = request.param(extras[i], extras[i + 1]);
        }
        return MAPPER.readTree(mvc.perform(request).andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString()).path("data");
    }

    private List<String> shelfIds(String auth, String... extras) throws Exception {
        List<String> ids = new ArrayList<>();
        shelf(auth, extras).path("items").forEach(item -> ids.add(item.path("id").asText()));
        return ids;
    }

    private long shelfTotal(String auth, String... extras) throws Exception {
        return shelf(auth, extras).path("total").asLong();
    }

    private List<JsonNode> relationCounts(String auth) throws Exception {
        String body = mvc.perform(get("/api/v1/contacts/relations").header("Authorization", auth))
                .andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString();
        JsonNode rows = MAPPER.readTree(body).path("data");
        List<JsonNode> out = new ArrayList<>();
        rows.forEach(out::add);
        return out;
    }

    private static java.util.Set<String> setOf(List<String> ids) {
        return new java.util.LinkedHashSet<>(ids);
    }

    @Test
    @DisplayName("the relation chip, the word and the window compose in one read")
    void wordRelationAndPageCompose() throws Exception {
        String auth = "Bearer " + register("rel-word-" + UUID.randomUUID() + "@example.com");
        String adaRef = createContact(auth, "Ada Byron", "referrer");
        String adaMen = createContact(auth, "Ada Asimov", "mentor");
        String adaPeer = createContact(auth, "Ada Turing", "referrer");
        String gracePeer = createContact(auth, "Grace Hopper", "peer");
        String alanPeer = createContact(auth, "Alan Turing", "peer");

        // One word, no chip: the whole registry, both Adas plus the rest.
        assertEquals(setOf(List.of(adaRef, adaMen, adaPeer)), setOf(shelfIds(auth, "q", "Ada")),
                "the word narrowed nothing");
        assertEquals(3, shelfTotal(auth, "q", "Ada"), "the word narrowed the total");

        // Chip alone: referrers only.
        assertEquals(setOf(List.of(adaPeer, adaRef)), setOf(shelfIds(auth, "relation", "referrer")),
                "the chip answered with rows behind the wrong chip");
        assertEquals(2, shelfTotal(auth, "relation", "referrer"), "the chip narrowed the total");

        // Word + chip: only Ada + referrer.
        assertEquals(setOf(List.of(adaPeer, adaRef)), setOf(shelfIds(auth, "q", "Ada", "relation", "referrer")),
                "the two narrowings did not compose");

        // Word + chip + page: two rows behind the narrowings, one per page of size 1.
        List<String> firstPage = shelfIds(auth, "q", "Ada", "relation", "referrer", "size", "1", "page", "0");
        List<String> secondPage = shelfIds(auth, "q", "Ada", "relation", "referrer", "size", "1", "page", "1");
        assertEquals(1, firstPage.size(), "the first window was empty");
        assertEquals(1, secondPage.size(), "the second window was empty");
        java.util.Set<String> firstAndSecond = new java.util.LinkedHashSet<>(firstPage);
        firstAndSecond.addAll(secondPage);
        assertEquals(setOf(List.of(adaPeer, adaRef)), firstAndSecond,
                "the two windows did not partition the narrowed shelf");
        // Page past the end: empty window, real total.
        assertEquals(List.of(), shelfIds(auth, "q", "Ada", "relation", "referrer", "size", "1", "page", "2"),
                "a page past the end answered with rows");
        assertEquals(2, shelfTotal(auth, "q", "Ada", "relation", "referrer"),
                "the window clamped the total instead of the page");
        // A case-insensitive chip: "REFERRER" chip and "Referrer" chip agree.
        assertEquals(setOf(shelfIds(auth, "relation", "referrer")), setOf(shelfIds(auth, "relation", "REFERRER")),
                "the chip is case-sensitive");
        // An empty relation: everyone.
        assertEquals(5, shelfTotal(auth, "relation", ""), "an empty relation is a filter");
    }

    @Test
    @DisplayName("the relations endpoint counts the rows behind each chip")
    void relationsCountsMatchTheList() throws Exception {
        String auth = "Bearer " + register("rel-count-" + UUID.randomUUID() + "@example.com");
        String referrer = createContact(auth, "Grace Hopper", "referrer");
        createContact(auth, "Alan Turing", "peer");
        createContact(auth, "Katherine Johnson", "peer");
        createContact(auth, "Barbara Liskov", "mentor");

        List<JsonNode> relations = relationCounts(auth);
        java.util.Map<String, Long> counts = new java.util.HashMap<>();
        for (JsonNode row : relations) {
            counts.put(row.path("relation").asText(), row.path("count").asLong());
        }
        assertEquals(2L, counts.getOrDefault("peer", 0L), "peer count is wrong");
        assertEquals(1L, counts.getOrDefault("referrer", 0L), "referrer count is wrong");
        assertEquals(1L, counts.getOrDefault("mentor", 0L), "mentor count is wrong");
        assertEquals(4, relations.stream().mapToLong(r -> r.path("count").asLong()).sum(),
                "the counts do not add up to the registry's size");
        // Counts order: biggest first.
        assertEquals("peer", relations.get(0).path("relation").asText(),
                "the most-used relation did not lead the chips");
        // The counts are the reader's own: another user's contacts are not counted.
        String stranger = "Bearer " + register("rel-stranger-" + UUID.randomUUID() + "@example.com");
        List<JsonNode> strangers = relationCounts(stranger);
        assertEquals(0, strangers.size(), "one reader's relations reached another reader's chips");
        // And the narrowing behind a chip includes the rows the chips said the reader holds.
        List<String> referrers = shelfIds(auth, "relation", "referrer");
        assertEquals(List.of(referrer), referrers, "the chip counts a row the list does not narrow to");
    }
}
