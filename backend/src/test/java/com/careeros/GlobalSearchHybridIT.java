package com.careeros;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.careeros.job.service.JobService;
import com.fasterxml.jackson.databind.JsonNode;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.web.servlet.MvcResult;

/**
 * {@code GET /api/v1/search}'s jobs channel as hybrid retrieval — the command palette's own query,
 * which had no integration coverage at all. The board's channel is pinned by {@link
 * JobSearchHybridIT}; this one was only ever read as text by a unit test, and its fused CTE sorted
 * by a column it never projected, so every global search against a real database answered 500
 * while every text assertion stayed green.
 *
 * <p>The vector space is partitioned by dimension on purpose: this suite's rows live in the last
 * two components, {@link JobSearchHybridIT}'s in the first two, so whichever order the two classes
 * run in, neither suite's rows can be recalled by the other's query.
 *
 * <p>The distance floor is pinned here as the cutoff it is rather than the relevance test its name
 * invites: {@link #theFloorIsADistanceCutoffSoANoiseTailStillAnswers()} holds a row 0.97 away and
 * drops the same shape 0.985 away, so a nonsense query still answers with noise.
 */
class GlobalSearchHybridIT extends ApiIntegrationTest {

    /**
     * One direction per test method. The two methods share the catalogue, so a direction that both
     * used would let the first method's rows into the second's vector pass -- each pair therefore
     * lives in its own two dimensions, and every other suite's rows sit in dimensions 0-1.
     */
    private static final List<Double> FUSE_QUERY =
            List.of(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.6, 0.8);
    /** Cosine distance 0.5 from {@link #FUSE_QUERY}: inside the floor, recallable but outranked. */
    private static final String FUSE_NEAR = "[0,0,0,0,0,0.866,0.3,0.4]";
    private static final List<Double> DEGRADE_QUERY =
            List.of(0.0, 0.0, 0.0, 0.0, 0.6, 0.8, 0.0, 0.0);
    private static final String DEGRADE_NEAR = "[0,0,0,0.866,0.3,0.4,0,0]";
    /**
     * Dimension 2 is the one this class, {@link JobSearchHybridIT} and every other suite leave at
     * zero, so this direction is orthogonal to every vector seeded in the IT database: cosine
     * distance 1.0 from all of them, past the floor, which is exactly "no measurable overlap".
     */
    private static final List<Double> ORTHOGONAL =
            List.of(0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0);

    /**
     * A sixteen-dimensional space of this test's own. The dimension guard pinned by {@link
     * #aRowWithMismatchedEmbeddingDimsIsSkippedNotAnError()} compares a query's width to each
     * row's, so these rows are invisible to every eight-dimensional query the rest of the suite
     * issues, and this query is invisible to every eight-dimensional row in the database. The
     * shared partition has no direction left to spare, and this case needs a query and a row that
     * are close without sharing a word.
     */
    private static final List<Double> NOISE_QUERY = List.of(
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0);
    /**
     * Cosine distance 0.97 from {@link #NOISE_QUERY}: the row's mass spread evenly over fifteen
     * dimensions with a 0.03 sliver on the one the query occupies. That sliver is the noise tail.
     * A dense row always parks a little mass wherever a sparse query points, and 0.03 of cosine
     * distance is 0.97 -- under the floor, so it is recalled. Measured on the 66 seeded dev roles
     * with the offline provider, a nonsense three-bucket query leaves 15 of them between 0.9614
     * and 0.9736 for exactly this reason.
     */
    private static final String NOISE_TAIL = "[" + "0.258083,".repeat(15) + "0.03]";
    /** The same shape 1.5 points further out, at cosine distance 0.985: past the floor, dropped. */
    private static final String NOISE_EDGE = "[" + "0.258170,".repeat(15) + "0.015]";
    /** The same dense shape with nothing at all on the query's dimension: cosine distance 1.0. */
    private static final String NOISE_ORTHOGONAL = "[" + "0.258199,".repeat(15) + "0]";

    @Autowired
    private JdbcTemplate jdbc;

    @Autowired
    private JobService jobService;

    private record Trio(String token, String lexicalHit, String paraphrase, String sibling) {
    }

    @Test
    @DisplayName("the jobs channel recalls a paraphrase no keyword pass can match")
    void hybridGlobalSearchRecallsAParaphrase() throws Exception {
        String auth = register("gsearch-fuse-" + UUID.randomUUID() + "@example.com");
        jobService.clearEmbeddingCache();
        Trio trio = seedTrio(auth, "[0,0,0,0,0,0,0.6,0.8]", FUSE_NEAR);
        ai.queryEmbedding = FUSE_QUERY;

        JsonNode jobs = search(auth, "payments platform " + trio.token());

        // Two rank-0 rows (one from each pass) fuse to 1/60; the rank-1 vector row to 1/61, so the
        // sibling is last and the paraphrase — which shares no word with the query — is recalled.
        assertThat(jobs.size()).isEqualTo(3);
        assertThat(List.of(id(jobs.get(0)), id(jobs.get(1))))
                .containsExactlyInAnyOrder(trio.lexicalHit(), trio.paraphrase());
        assertThat(id(jobs.get(2)))
                .as("the rank-1 vector row must fuse below both rank-0 rows")
                .isEqualTo(trio.sibling());
    }

    @Test
    @DisplayName("degradation: no vector keeps the keyword meaning, and noise still answers nothing")
    void globalSearchDegradesToKeywordOnly() throws Exception {
        String auth = register("gsearch-degrade-" + UUID.randomUUID() + "@example.com");
        Trio trio = seedTrio(auth, "[0,0,0,0,0.6,0.8,0,0]", DEGRADE_NEAR);

        // Provider down (or missing): an empty answer must leave the channel exactly as the
        // keyword search it replaced, not fail the palette the user typed into.
        jobService.clearEmbeddingCache();
        ai.queryEmbedding = List.of();
        JsonNode keywordOnly = search(auth, "payments platform " + trio.token());
        assertThat(keywordOnly.size()).isEqualTo(1);
        assertThat(id(keywordOnly.get(0))).isEqualTo(trio.lexicalHit());

        // A direction no row points at: the floor answers zero rows instead of the 50 nearest.
        jobService.clearEmbeddingCache();
        ai.queryEmbedding = ORTHOGONAL;
        assertThat(search(auth, "nosuchrole" + trio.token()).size()).isZero();
    }

    @Test
    @DisplayName("dimension mismatch: an incompatible row is skipped, not a 500 on the whole palette")
    void aRowWithMismatchedEmbeddingDimsIsSkippedNotAnError() throws Exception {
        String auth = register("gsearch-dim-" + UUID.randomUUID() + "@example.com");
        jobService.clearEmbeddingCache();
        // This case seeds no vector of its own: the query vector is what the pass must survive, and
        // a row in a direction the other cases use would leak into their result sets.
        String token = "gsh" + Long.toString(Math.abs(UUID.randomUUID().getMostSignificantBits()), 36);
        String lexicalHit = createJob(auth, "Payments Platform Engineer " + token, "Delta" + token);
        // pgvector raises "different vector dimensions" for the distance operator rather than
        // skipping the row, so an unguarded pass fails the whole search -- every group the palette
        // draws -- over one row a provider switch left behind.
        String mismatched = createJob(auth, "Contract Engineer " + token, "Epsilon" + token);
        vector(mismatched, "[0,0,1]");

        ai.queryEmbedding = FUSE_QUERY;
        JsonNode jobs = search(auth, "payments platform " + token);

        // The search answers, and the unrankable row is simply absent -- the same trade the board's
        // own pass makes. (Asserted by membership, not by size: the vector pass is catalogue-wide
        // here, so the other cases' rows may legitimately share the page.)
        List<String> ids = jobs.findValuesAsText("id");
        assertThat(ids).contains(lexicalHit).doesNotContain(mismatched);
    }

    @Test
    @DisplayName("the floor is a distance cutoff, not a relevance test: a noise tail still answers")
    void theFloorIsADistanceCutoffSoANoiseTailStillAnswers() throws Exception {
        String auth = register("gsearch-noise-" + UUID.randomUUID() + "@example.com");
        jobService.clearEmbeddingCache();
        String token = "gsn" + Long.toString(Math.abs(UUID.randomUUID().getMostSignificantBits()), 36);
        String tail = createJob(auth, "Warehouse Operative " + token, "Zeta" + token);
        String edge = createJob(auth, "Night Auditor " + token, "Eta" + token);
        String orthogonal = createJob(auth, "Night Porter " + token, "Theta" + token);
        vector(tail, NOISE_TAIL);
        vector(edge, NOISE_EDGE);
        vector(orthogonal, NOISE_ORTHOGONAL);

        ai.queryEmbedding = NOISE_QUERY;
        JsonNode jobs = search(auth, "qqqzzz" + token);

        // Three rows, not one word in common with the query, spanning 1.5 points of cosine
        // distance, and the only thing that separates them is which side of 0.98 they land on. The
        // floor reads like a relevance test and is not one: it is a number on a dial, and a dense
        // row's noise tail under a sparse query lands under it. That is what EVALUATION.md means
        // by retrieval quality under the offline provider not being a measurement to act on.
        assertThat(jobs.findValuesAsText("id"))
                .as("0.97 is recalled as a match; 0.985 and exactly 1.0 are not")
                .containsExactly(tail);
    }

    /** Three recall paths: a lexical hit, a paraphrase no keyword pass sees, a vector-only sibling. */
    private Trio seedTrio(String auth, String paraphraseVector, String siblingVector)
            throws Exception {
        String token = "gsh" + Long.toString(Math.abs(UUID.randomUUID().getMostSignificantBits()), 36);
        String lexicalHit = createJob(auth, "Payments Platform Engineer " + token, "Alpha" + token);
        String paraphrase = createJob(auth, "Backend Engineer " + token, "Beta" + token);
        String sibling = createJob(auth, "Payments Analyst " + token, "Gamma" + token);
        vector(paraphrase, paraphraseVector);
        vector(sibling, siblingVector);
        return new Trio(token, lexicalHit, paraphrase, sibling);
    }

    private String createJob(String auth, String title, String company) throws Exception {
        MvcResult res = mvc.perform(post("/api/v1/jobs")
                        .header("Authorization", "Bearer " + auth)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(Map.of("title", title,
                                "company", Map.of("name", company),
                                "location", "Remote",
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

    private JsonNode search(String auth, String q) throws Exception {
        MvcResult res = mvc.perform(get("/api/v1/search")
                        .header("Authorization", "Bearer " + auth)
                        .param("q", q))
                .andExpect(status().isOk())
                .andReturn();
        return MAPPER.readTree(res.getResponse().getContentAsString()).path("data").path("jobs");
    }

    private static String id(JsonNode job) {
        return job.path("id").asText();
    }
}
