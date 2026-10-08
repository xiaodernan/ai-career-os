package com.careeros;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.careeros.job.service.JobService;
import com.fasterxml.jackson.databind.JsonNode;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.web.servlet.MvcResult;

/**
 * GET /api/v1/jobs as hybrid retrieval: the keyword/tsvector pass and the pgvector cosine-distance
 * pass ranked over one filtered row set and fused by reciprocal rank, the way the agent's
 * {@code search_jobs} tool already fuses them (ai-service {@code agents/tools.py}).
 *
 * <p>Three roles, each a different recall path: a lexical hit (shares both query words), a
 * paraphrase (shares none, so only the vector pass can find it), and a sibling (vector near the
 * query but no keyword match). The fake ai-service answers whatever vector this test hands it, so
 * the suite needs no embedding provider: the degradation cases are an empty answer (provider down)
 * and a direction orthogonal to every row (the distance floor, which drops what shares no
 * dimension with the query and keeps the sliver that shares one -- {@link GlobalSearchHybridIT}
 * pins both sides of that line).
 */
class JobSearchHybridIT extends ApiIntegrationTest {

    private static final List<Double> QUERY = List.of(1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0);
    /** Cosine distance 0.5 from {@link #QUERY}: inside the floor, so recallable but outranked. */
    private static final String NEAR = "[0.5,0.8660254,0,0,0,0,0,0]";
    /** Cosine distance 1.0 from every seeded row: beyond the floor, i.e. "no measurable overlap". */
    private static final String ORTHOGONAL = "[0,0,1,0,0,0,0,0]";

    @Autowired
    private JdbcTemplate jdbc;

    @Autowired
    private JobService jobService;

    private record Board(String token, String lexicalHit, String paraphrase, String sibling) {
    }

    @Test
    @DisplayName("relevance search recalls a paraphrase no keyword pass can match (the gap)")
    void relevanceSearchFusesKeywordMatchesWithVectorRecall() throws Exception {
        String auth = register("hybrid-fuse-" + UUID.randomUUID() + "@example.com");
        jobService.clearEmbeddingCache();
        Board board = seedBoard(auth);
        ai.queryEmbedding = QUERY;

        JsonNode data = search(auth, board.token(), "payments platform", null);
        assertThat(data.path("total").asInt()).isEqualTo(3);
        assertThat(ids(data)).contains(board.lexicalHit, board.paraphrase, board.sibling);
        // Reciprocal ranks: 1/60 for each rank-0 pass, 1/61 for the rank-1 vector row, so the
        // sibling is last whatever the insertion order was.
        assertThat(data.path("items").get(2).path("id").asText())
                .as("the vector row ranked 1 must fuse below both rank-0 rows")
                .isEqualTo(board.sibling);

        // An explicit ordering is a different question: sort=posted orders the lexical matches,
        // it does not switch retrieval on.
        JsonNode posted = search(auth, board.token(), "payments platform", "posted");
        assertThat(posted.path("total").asInt())
                .as("an explicit sort orders rows, it must not rank by distance")
                .isEqualTo(1);
        assertThat(ids(posted)).containsExactly(board.lexicalHit);
    }

    @Test
    @DisplayName("degradation: no vector means keyword-only, and orthogonal noise answers zero")
    void withoutAUsableVectorTheSearchAnswersKeywordOnlyAndNoiseStaysZero() throws Exception {
        String auth = register("hybrid-degrade-" + UUID.randomUUID() + "@example.com");
        Board board = seedBoard(auth);

        // The provider is down (or missing): the embedder answers an empty list and the search
        // keeps the exact keyword meaning it had before vectors existed.
        jobService.clearEmbeddingCache();
        ai.queryEmbedding = List.of();
        JsonNode keywordOnly = search(auth, board.token(), "payments platform", null);
        assertThat(keywordOnly.path("total").asInt()).isEqualTo(1);
        assertThat(ids(keywordOnly)).containsExactly(board.lexicalHit);

        // A direction nothing in the catalogue points at: the distance floor excludes every row
        // instead of handing back the 50 nearest roles as "matches" for a nonsense query.
        jobService.clearEmbeddingCache();
        ai.queryEmbedding = doubles(ORTHOGONAL);
        JsonNode noise = search(auth, board.token(), "nosuchrole" + board.token(), null);
        assertThat(noise.path("total").asInt())
                .as("noise must answer zero rows, not ranked neighbours")
                .isZero();
        assertThat(noise.path("items").isEmpty()).isTrue();
    }

    /** Creates the three recall paths and seeds vectors for everything the keyword pass misses. */
    private Board seedBoard(String auth) throws Exception {
        String token = "hyb" + Long.toString(Math.abs(UUID.randomUUID().getMostSignificantBits()), 36);
        // The location doubles as this board's namespace: the catalogue is shared with every
        // other integration test, so each search is faceted to the rows this test created.
        String lexicalHit = createJob(auth, "Payments Platform Engineer " + token, "Alpha" + token, token);
        String paraphrase = createJob(auth, "Backend Engineer " + token, "Beta" + token, token);
        String sibling = createJob(auth, "Payments Analyst " + token, "Gamma" + token, token);
        // The lexical hit keeps a null vector on purpose: a job the embedding job has not reached
        // yet must still be recallable, which the union guarantees because keyword rank is enough.
        vector(paraphrase, "[1,0,0,0,0,0,0,0]");
        vector(sibling, NEAR);
        return new Board(token, lexicalHit, paraphrase, sibling);
    }

    private String createJob(String auth, String title, String company, String location) throws Exception {
        MvcResult res = mvc.perform(post("/api/v1/jobs")
                        .header("Authorization", "Bearer " + auth)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(Map.of("title", title,
                                "company", Map.of("name", company),
                                "location", location,
                                "description", "Backend role: " + title,
                                "skills", List.of("Java")))))
                .andExpect(status().isCreated())
                .andReturn();
        return MAPPER.readTree(res.getResponse().getContentAsString()).path("data").path("id").asText();
    }

    /** The embedding column takes pgvector's text form; the value is data, never SQL. */
    private void vector(String jobId, String literal) {
        jdbc.update("UPDATE jobs SET embedding = CAST(? AS vector) WHERE id = ?",
                literal, UUID.fromString(jobId));
    }

    private JsonNode search(String auth, String token, String q, String sort) throws Exception {
        var request = get("/api/v1/jobs")
                .header("Authorization", "Bearer " + auth)
                .param("location", token)
                .param("page", "0").param("size", "20");
        if (q != null) {
            request = request.param("q", q);
        }
        if (sort != null) {
            request = request.param("sort", sort);
        }
        MvcResult res = mvc.perform(request).andExpect(status().isOk()).andReturn();
        return MAPPER.readTree(res.getResponse().getContentAsString()).path("data");
    }

    private static Set<String> ids(JsonNode data) {
        Set<String> out = new LinkedHashSet<>();
        for (JsonNode item : data.path("items")) {
            out.add(item.path("id").asText());
        }
        return out;
    }

    private static List<Double> doubles(String vectorLiteral) {
        String inner = vectorLiteral.substring(1, vectorLiteral.length() - 1);
        return List.of(inner.split(",")).stream().map(Double::valueOf).toList();
    }

    @Test
    @DisplayName("dimension mismatch: rows with incompatible embedding dims are skipped, not a 500")
    void aRowWithMismatchedEmbeddingDimsIsSkippedNotAnError() throws Exception {
        String auth = register("hybrid-dim-" + UUID.randomUUID() + "@example.com");
        jobService.clearEmbeddingCache();
        Board board = seedBoard(auth);
        // A fourth row with a 3-dim vector (the query is 8-dim): the CASE guard must skip it
        // instead of throwing a dimension-mismatch error. It should not appear in results.
        String mismatched = createJob(auth, "Contract Engineer " + board.token(), "Delta" + board.token(), board.token());
        vector(mismatched, "[1,0,0]"); // 3-dim vs 8-dim query -> incompatible

        ai.queryEmbedding = QUERY;
        JsonNode data = search(auth, board.token(), "payments platform", null);
        // The search must succeed (200) and the mismatched row must be excluded from the vector pass
        // (keyword pass also doesn't match "payments platform" on its title).
        assertThat(data.path("total").asInt())
                .as("dimension mismatch must not 500; incompatible row is simply skipped")
                .isEqualTo(3);
        assertThat(ids(data)).containsExactlyInAnyOrder(board.lexicalHit, board.paraphrase, board.sibling);
    }

    @Test
    @DisplayName("browsing never pays for an embedding: no query means no vector fetch")
    void browsingNeverFetchesAnEmbedding() throws Exception {
        String auth = register("hybrid-browse-" + UUID.randomUUID() + "@example.com");
        jobService.clearEmbeddingCache();
        Board board = seedBoard(auth);
        // Even with a provider ready to answer, a browse (no q) must not ask: the vector
        // is only ever fetched for a relevance search, so scrolling the board stays free.
        ai.calls.clear();
        ai.queryEmbedding = QUERY;
        JsonNode data = search(auth, board.token(), null, null);
        assertThat(data.path("total").asInt()).isEqualTo(3);
        assertThat(ids(data)).containsExactlyInAnyOrder(board.lexicalHit, board.paraphrase, board.sibling);
        assertThat(ai.calls)
                .as("a browse must not call the embedder at all")
                .doesNotContain("embedQuery");
    }
}
