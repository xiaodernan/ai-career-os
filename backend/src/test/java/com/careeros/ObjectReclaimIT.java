package com.careeros;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.request.MockMultipartHttpServletRequestBuilder;

/**
 * What a delete owes the bytes an upload stored (roadmap 44.2).
 *
 * <p>An upload is one object behind two rows: the resume serves the file as its original, and the
 * document row is the copy the AI quotes from. So the object goes with the last row that names it,
 * and which delete that is depends on the table, not on the route the reader pressed. The unit tests
 * pin that decision; this pins it against the real transaction manager and the real flushes, because
 * the claim is about rows actually gone. A reclaim that asked while its own transaction still held
 * the resume row would answer "still referenced" and leave the file behind for good, and a delete
 * that reclaimed before the rows were durable would destroy bytes a page still serves.
 */
class ObjectReclaimIT extends ApiIntegrationTest {

    private static final byte[] PDF = ("%PDF-1.4\n% mock resume bytes\n1 0 obj\ntrailer\n%%EOF\n")
            .getBytes(StandardCharsets.UTF_8);

    @Test
    @DisplayName("deleting the resume reclaims the object its upload stored")
    void deletingAResumeReclaimsItsUpload() throws Exception {
        String alice = register("reclaim-resume-" + UUID.randomUUID() + "@example.com");
        Uploaded upload = resumeUpload(alice);

        mvc.perform(delete("/api/v1/resumes/" + upload.data().path("resumeId").asText())
                        .header("Authorization", "Bearer " + alice))
                .andExpect(status().isNoContent());

        assertFalse(storage.store.containsKey(upload.fileKey()),
                "the resume and its ingested copy were the only rows naming " + upload.fileKey());
        // The same delete takes the copy out of the list, so nothing left can quote it.
        mvc.perform(get("/api/v1/knowledge/sources").header("Authorization", "Bearer " + alice))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.total").value(0));
    }

    @Test
    @DisplayName("deleting the knowledge copy leaves the resume its original file")
    void deletingASourceKeepsAResumeUpload() throws Exception {
        String alice = register("reclaim-source-" + UUID.randomUUID() + "@example.com");
        Uploaded upload = resumeUpload(alice);

        mvc.perform(delete("/api/v1/knowledge/sources/" + upload.data().path("sourceId").asText())
                        .header("Authorization", "Bearer " + alice))
                .andExpect(status().isNoContent());

        assertTrue(storage.store.containsKey(upload.fileKey()),
                "the resume still serves the bytes its upload stored, so taking them is not this "
                        + "delete's to make");
        // and the page that serves them still does, with the copy retired underneath it.
        mvc.perform(get("/api/v1/resumes/" + upload.data().path("resumeId").asText() + "/file")
                        .header("Authorization", "Bearer " + alice))
                .andExpect(status().isOk());
    }

    @Test
    @DisplayName("deleting a knowledge upload reclaims its object")
    void deletingAKnowledgeUploadReclaimsIt() throws Exception {
        String alice = register("reclaim-doc-" + UUID.randomUUID() + "@example.com");
        Uploaded upload = documentUpload(alice);

        mvc.perform(delete("/api/v1/knowledge/sources/" + upload.data().path("sourceId").asText())
                        .header("Authorization", "Bearer " + alice))
                .andExpect(status().isNoContent());

        assertFalse(storage.store.containsKey(upload.fileKey()),
                "nothing but the retired audit row names the upload's object");
    }

    @Test
    @DisplayName("deleting a source that stored no object leaves every object alone")
    void deletingAnInlineTextSourceReclaimsNothing() throws Exception {
        String alice = register("reclaim-text-" + UUID.randomUUID() + "@example.com");
        MvcResult result = mvc.perform(post("/api/v1/knowledge/text")
                        .header("Authorization", "Bearer " + alice)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"title\":\"Kubernetes guide\",\"text\":\"rebash --help output\","
                                + "\"kind\":\"note\"}"))
                .andExpect(status().isOk())
                .andReturn();
        String sourceId = MAPPER.readTree(result.getResponse().getContentAsString())
                .path("data").path("sourceId").asText();
        Set<String> before = Set.copyOf(storage.store.keySet());

        mvc.perform(delete("/api/v1/knowledge/sources/" + sourceId)
                        .header("Authorization", "Bearer " + alice))
                .andExpect(status().isNoContent());

        // An inline text ingest names no key, so the reclaim asks nothing of the store -- and a
        // blank key handed to it would be a delete of whatever the next byte-less row happened to
        // be sitting on.
        assertEquals(before, Set.copyOf(storage.store.keySet()), "a keyless delete removed an object");
    }

    @Test
    @DisplayName("a delete another account's row refuses reclaims nothing")
    void aRefusedDeleteReclaimsNothing() throws Exception {
        String alice = register("reclaim-alice-" + UUID.randomUUID() + "@example.com");
        String bob = register("reclaim-bob-" + UUID.randomUUID() + "@example.com");
        Uploaded upload = resumeUpload(alice);
        String resumeId = upload.data().path("resumeId").asText();

        // 404, not 403: the row is invisible to bob, and an invisible row's file is not his to take.
        mvc.perform(delete("/api/v1/resumes/" + resumeId).header("Authorization", "Bearer " + bob))
                .andExpect(status().isNotFound());

        assertTrue(storage.store.containsKey(upload.fileKey()),
                "a refused delete of another account's resume touched a file");
        mvc.perform(get("/api/v1/resumes/" + resumeId + "/file").header("Authorization", "Bearer " + alice))
                .andExpect(status().isOk());
    }

    private Uploaded resumeUpload(String token) throws Exception {
        return upload(multipart("/api/v1/resumes/upload")
                .file(new MockMultipartFile("file", "resume.pdf", "application/pdf", PDF)), token);
    }

    private Uploaded documentUpload(String token) throws Exception {
        return upload(multipart("/api/v1/knowledge/documents")
                .file(new MockMultipartFile("file", "certificate.txt", "text/plain",
                        "Certified in something, 2024.\n".getBytes(StandardCharsets.UTF_8))), token);
    }

    /**
     * Perform a multipart upload and return its answer together with the key the store grew by. No
     * route names that key -- it is the object store's own identifier -- so the delta over the keys
     * held before the upload is the only honest way to point at it.
     */
    private Uploaded upload(MockMultipartHttpServletRequestBuilder request, String token) throws Exception {
        Set<String> before = Set.copyOf(storage.store.keySet());
        MvcResult result = mvc.perform(request.header("Authorization", "Bearer " + token))
                .andExpect(status().isCreated())
                .andReturn();
        JsonNode data = MAPPER.readTree(result.getResponse().getContentAsString()).path("data");
        List<String> grown = storage.store.keySet().stream().filter(key -> !before.contains(key)).toList();
        assertEquals(1, grown.size(), "the upload stored " + grown + " on top of " + before.size() + " keys");
        return new Uploaded(data, grown.get(0));
    }

    /** One upload: the ids its route answered with, and the one object it put in the store. */
    private record Uploaded(JsonNode data, String fileKey) {
    }
}
