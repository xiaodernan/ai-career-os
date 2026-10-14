package com.careeros;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.web.servlet.MvcResult;

/**
 * Business-domain API contract + security tests. The headline concern is tenant isolation: a
 * resource created by one user must be invisible (HTTP 404, never 403, so existence is not
 * leaked) to every other user, across all user-owned aggregates. Also covers the resume upload
 * multipart flow, the nested-company job-create path, and application status handling.
 */
class DomainApiIT extends ApiIntegrationTest {

    private static String authHeader() {
        return "Authorization";
    }

    private MvcResult createResume(String token, String title) throws Exception {
        return mvc.perform(post("/api/v1/resumes")
                        .header(authHeader(), "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(Map.of("title", title,
                                "plaintext", "Zhang San\nBackend Engineer\nEXPERIENCE\nAcme 2021-2024\n- built services in Java"))))
                .andExpect(status().isCreated())
                .andReturn();
    }

    private static String dataId(MvcResult r) throws Exception {
        return MAPPER.readTree(r.getResponse().getContentAsString()).path("data").path("id").asText();
    }

    @Test
    @DisplayName("resumes are invisible to other users (404, not 403) on every verb")
    void resumeCrossUserIsolation() throws Exception {
        String alice = register("iso-alice-" + UUID.randomUUID() + "@example.com");
        String bob = register("iso-bob-" + UUID.randomUUID() + "@example.com");

        String resumeId = dataId(createResume(alice, "Alice Resume"));

        // Owner can read.
        mvc.perform(get("/api/v1/resumes/" + resumeId).header(authHeader(), "Bearer " + alice))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.id").value(resumeId));

        // Non-owner is refused on read/update/parse/delete with 404 (no existence leak).
        mvc.perform(get("/api/v1/resumes/" + resumeId).header(authHeader(), "Bearer " + bob))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error.code").value("RESUME_NOT_FOUND"));
        mvc.perform(patch("/api/v1/resumes/" + resumeId).header(authHeader(), "Bearer " + bob)
                        .contentType(MediaType.APPLICATION_JSON).content(json(Map.of("title", "hijacked"))))
                .andExpect(status().isNotFound());
        mvc.perform(post("/api/v1/resumes/" + resumeId + "/parse").header(authHeader(), "Bearer " + bob))
                .andExpect(status().isNotFound());
        mvc.perform(delete("/api/v1/resumes/" + resumeId).header(authHeader(), "Bearer " + bob))
                .andExpect(status().isNotFound());

        // Bob's list must not contain Alice's resume.
        mvc.perform(get("/api/v1/resumes").header(authHeader(), "Bearer " + bob))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.total").value(0));
        // Alice's list must.
        mvc.perform(get("/api/v1/resumes").header(authHeader(), "Bearer " + alice))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.total").value(1));

        // The 404 attempts must not have mutated anything: Alice can still read the original title.
        mvc.perform(get("/api/v1/resumes/" + resumeId).header(authHeader(), "Bearer " + alice))
                .andExpect(jsonPath("$.data.title").value("Alice Resume"));
    }

    @Test
    @DisplayName("unauthenticated requests to protected resources are rejected with 401")
    void requiresAuthentication() throws Exception {
        String alice = register("iso-anon-" + UUID.randomUUID() + "@example.com");
        String resumeId = dataId(createResume(alice, "Private"));

        mvc.perform(get("/api/v1/resumes/" + resumeId)).andExpect(status().isUnauthorized());
        mvc.perform(get("/api/v1/resumes/" + resumeId).header(authHeader(), "Bearer not-a-real-token"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    @DisplayName("uploading a resume stores bytes, registers a knowledge source, and calls the AI ingest")
    void resumeUploadHappyPath() throws Exception {
        String alice = register("up-" + UUID.randomUUID() + "@example.com");
        byte[] pdf = ("%PDF-1.4\n% mock resume bytes\n1 0 obj\ntrailer\n%%EOF\n")
                .getBytes(StandardCharsets.UTF_8);

        MvcResult res = mvc.perform(multipart("/api/v1/resumes/upload")
                        .file(new MockMultipartFile("file", "resume.pdf", "application/pdf", pdf))
                        .header(authHeader(), "Bearer " + alice))
                .andExpect(status().isCreated())
                .andReturn();
        JsonNode data = MAPPER.readTree(res.getResponse().getContentAsString()).path("data");
        String resumeId = data.path("resumeId").asText();
        assertNotNull(data.path("documentId").asText());
        assertFalse(data.path("sourceId").asText().isBlank(), "a knowledge source must be linked");
        assertFalse(data.path("taskId").asText().isBlank(), "ingestion task id expected from ai-service");

        // AI ingest was invoked, and the object landed in storage under the user's folder.
        assertTrue(ai.calls.contains("ingestDocument"), "expected ingestDocument call");
        assertTrue(storage.store.keySet().stream().anyMatch(k -> k.contains("/resumes/") && k.endsWith(".pdf")),
                "expected the pdf key in object storage");

        // The uploaded resume and its knowledge source are both visible to the owner.
        mvc.perform(get("/api/v1/resumes").header(authHeader(), "Bearer " + alice))
                .andExpect(jsonPath("$.data.total").value(1));
        MvcResult sources = mvc.perform(get("/api/v1/knowledge/sources").header(authHeader(), "Bearer " + alice))
                .andExpect(status().isOk())
                .andReturn();
        JsonNode items = MAPPER.readTree(sources.getResponse().getContentAsString())
                .path("data").path("items");
        assertEquals(1, items.size());
        assertEquals("resume", items.get(0).path("kind").asText());
        assertEquals(resumeId, items.get(0).path("refId").asText());
    }

    @Test
    @DisplayName("uploads of unsupported file types are rejected and never stored")
    void resumeUploadRejectsUnsupportedType() throws Exception {
        String alice = register("upbad-" + UUID.randomUUID() + "@example.com");
        byte[] notADoc = new byte[] {0x00, 0x01, 0x02, (byte) 0xFF, (byte) 0xFE, 0x00, 0x09, 0x0A};

        mvc.perform(multipart("/api/v1/resumes/upload")
                        .file(new MockMultipartFile("file", "mystery.bin", "application/octet-stream", notADoc))
                        .header(authHeader(), "Bearer " + alice))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("INVALID_FILE_TYPE"));

        mvc.perform(get("/api/v1/resumes").header(authHeader(), "Bearer " + alice))
                .andExpect(jsonPath("$.data.total").value(0));
    }

    @Test
    @DisplayName("when ai-service ingest fails the upload surfaces 502, not a phantom success")
    void resumeUploadAiOutagePropagates() throws Exception {
        String alice = register("upfail-" + UUID.randomUUID() + "@example.com");
        ai.failIngest = true;
        byte[] pdf = "%PDF-1.4\nwill not ingest\n%%EOF\n".getBytes(StandardCharsets.UTF_8);

        mvc.perform(multipart("/api/v1/resumes/upload")
                        .file(new MockMultipartFile("file", "resume.pdf", "application/pdf", pdf))
                        .header(authHeader(), "Bearer " + alice))
                .andExpect(status().isBadGateway())
                .andExpect(jsonPath("$.error.code").value("AI_SERVICE_ERROR"));
    }

    @Test
    @DisplayName("the original file downloads back to its owner, and to nobody else")
    void resumeOriginalFileDownloadsForItsOwnerOnly() throws Exception {
        String alice = register("dl-" + UUID.randomUUID() + "@example.com");
        String bob = register("dlx-" + UUID.randomUUID() + "@example.com");
        byte[] pdf = ("%PDF-1.4\n% download me\n1 0 obj\ntrailer\n%%EOF\n")
                .getBytes(StandardCharsets.UTF_8);

        MvcResult up = mvc.perform(multipart("/api/v1/resumes/upload")
                        .file(new MockMultipartFile("file", "resume.pdf", "application/pdf", pdf))
                        .header(authHeader(), "Bearer " + alice))
                .andExpect(status().isCreated())
                .andReturn();
        String resumeId = MAPPER.readTree(up.getResponse().getContentAsString())
                .path("data").path("resumeId").asText();

        // The owner gets the exact bytes back, typed as stored, named for saving.
        MvcResult dl = mvc.perform(get("/api/v1/resumes/" + resumeId + "/file")
                        .header(authHeader(), "Bearer " + alice))
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.APPLICATION_PDF))
                .andExpect(header().string("Content-Disposition",
                        org.hamcrest.Matchers.containsString("attachment")))
                .andReturn();
        assertArrayEquals(pdf, dl.getResponse().getContentAsByteArray(),
                "the download must be the uploaded bytes, not a re-encode");

        // Another account's resume id is not a file: the route is user-scoped like every read.
        mvc.perform(get("/api/v1/resumes/" + resumeId + "/file")
                        .header(authHeader(), "Bearer " + bob))
                .andExpect(status().isNotFound());
        mvc.perform(get("/api/v1/resumes/" + resumeId + "/file"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    @DisplayName("a resume created by hand has no original file, and says so")
    void handCreatedResumeHasNoFileToDownload() throws Exception {
        String alice = register("dlnone-" + UUID.randomUUID() + "@example.com");
        String resumeId = dataId(createResume(alice, "Pasted only"));

        mvc.perform(get("/api/v1/resumes/" + resumeId + "/file")
                        .header(authHeader(), "Bearer " + alice))
                .andExpect(status().isNotFound());
    }

    @Test
    @DisplayName("a growth report's second run diffs against the stored one, per user")
    void growthReportSecondRunDiffsAgainstTheStoredOne() throws Exception {
        String alice = register("gr-" + UUID.randomUUID() + "@example.com");
        String bob = register("grx-" + UUID.randomUUID() + "@example.com");
        String body = "{\"targetRole\":\"Senior Backend Engineer (Java)\"}";

        // First run: nothing stored yet, the progress block is a baseline.
        mvc.perform(post("/api/v1/growth-report").header(authHeader(), "Bearer " + alice)
                        .contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.readiness.verdict").value("not_ready"))
                .andExpect(jsonPath("$.data.progress.baseline").value(true));

        // Second run, same role: the service fed the stored gap block to the engine, so
        // the diff is against an observation, not a browser-held copy.
        mvc.perform(post("/api/v1/growth-report").header(authHeader(), "Bearer " + alice)
                        .contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.progress.baseline").value(false));

        // Another account, same role: its first run is its own baseline — the storage is
        // user-scoped like every table in this schema.
        mvc.perform(post("/api/v1/growth-report").header(authHeader(), "Bearer " + bob)
                        .contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.progress.baseline").value(true));

        mvc.perform(post("/api/v1/growth-report")
                        .contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isUnauthorized());
    }

    @Test
    @DisplayName("job create with a nested company persists the company name (regression)")
    void jobCreateWithNestedCompany() throws Exception {
        String alice = register("job-" + UUID.randomUUID() + "@example.com");
        // Unique token: the board is shared across users, so listing assertions must
        // filter to this job instead of depending on table totals.
        String token = "qx" + Long.toString(Math.abs(UUID.randomUUID().getMostSignificantBits()), 36);
        String title = "Backend Engineer, Payments " + token;
        Map<String, Object> body = Map.of(
                "title", title,
                "company", Map.of("name", "TechCorp", "industry", "fintech"),
                "location", "Hangzhou",
                "description", "We are hiring a backend engineer for the payments platform.",
                "requirements", List.of("Java", "Spring Boot"),
                "skills", List.of("Java", "Redis", "Kafka"));

        MvcResult res = mvc.perform(post("/api/v1/jobs")
                        .header(authHeader(), "Bearer " + alice)
                        .contentType(MediaType.APPLICATION_JSON).content(json(body)))
                .andExpect(status().isCreated())
                .andReturn();
        JsonNode data = MAPPER.readTree(res.getResponse().getContentAsString()).path("data");
        assertEquals("TechCorp", data.path("companyName").asText(), "company.name must be persisted");
        String jobId = data.path("id").asText();
        assertNotNull(data.path("companyId").asText());

        // Save then re-open: the detail reflects the saved flag and the shared company.
        mvc.perform(post("/api/v1/jobs/" + jobId + "/save")
                        .header(authHeader(), "Bearer " + alice)
                        .contentType(MediaType.APPLICATION_JSON).content(json(Map.of("note", "top choice"))))
                .andExpect(status().isOk());
        mvc.perform(get("/api/v1/jobs/" + jobId).header(authHeader(), "Bearer " + alice))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.company.name").value("TechCorp"))
                .andExpect(jsonPath("$.data.saved").value(true));

        // The board listing exercises the native search SQL (facets + LIMIT/OFFSET bind).
        mvc.perform(get("/api/v1/jobs?q=" + token + "&page=0&size=5&sort=posted")
                        .header(authHeader(), "Bearer " + alice))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.total").value(1))
                .andExpect(jsonPath("$.data.size").value(5))
                .andExpect(jsonPath("$.data.items[0].id").value(jobId))
                .andExpect(jsonPath("$.data.items[0].title").value(title))
                .andExpect(jsonPath("$.data.items[0].companyName").value("TechCorp"));
        mvc.perform(get("/api/v1/jobs?q=" + token + "&location=Hangzhou&skills=Java&sort=match")
                        .header(authHeader(), "Bearer " + alice))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.items[0].id").value(jobId));
        mvc.perform(get("/api/v1/jobs?q=nosuchrole" + token)
                        .header(authHeader(), "Bearer " + alice))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.total").value(0))
                .andExpect(jsonPath("$.data.items").isEmpty());
    }

    /**
     * A job created through the nested-company path, with the researched fields the company page
     * reads back. Returns the created {@code JobListItem}: its {@code id} is the job and its
     * {@code companyId} the company the upsert produced.
     */
    private JsonNode createJobWithResearchedCompany(String token, String companyName, String title)
            throws Exception {
        Map<String, Object> body = Map.of(
                "title", title,
                "company", Map.of("name", companyName, "industry", "fintech",
                        "culture", "Engineer-led, remote-first.",
                        "interviewProcess", "Screen → Tech → HR",
                        "sources", List.of(Map.of("type", "user_paste", "note", "Researched by hand."))),
                "location", "Remote",
                "description", "We are hiring for " + title + ".",
                "skills", List.of("Java"));
        MvcResult res = mvc.perform(post("/api/v1/jobs")
                        .header(authHeader(), "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON).content(json(body)))
                .andExpect(status().isCreated())
                .andReturn();
        return MAPPER.readTree(res.getResponse().getContentAsString()).path("data");
    }

    @Test
    @DisplayName("a company page carries the researched profile and only its own open roles")
    void companyDetailCarriesTheProfileAndOnlyItsOwnRoles() throws Exception {
        String alice = register("co-" + UUID.randomUUID() + "@example.com");
        String token = "co" + Long.toString(Math.abs(UUID.randomUUID().getMostSignificantBits()), 36);
        String name = "Acme Research " + token;
        // A sibling whose name *contains* the first one. The board's `?company=` facet is an ILIKE
        // over the name and is right to include it; a profile page that listed a sibling's role would
        // be a wrong answer wearing the same word, which is why the company scope is an id.
        String siblingName = name + " Labs";

        JsonNode mine = createJobWithResearchedCompany(alice, name, "Backend Engineer " + token);
        JsonNode sibling = createJobWithResearchedCompany(alice, siblingName, "Data Engineer " + token);

        mvc.perform(get("/api/v1/companies/" + mine.path("companyId").asText())
                        .header(authHeader(), "Bearer " + alice))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.company.name").value(name))
                // `culture`, `interviewProcess` and `sources` were accepted on write and carried by no
                // read path at all, so a researched profile could be posted and never seen again.
                .andExpect(jsonPath("$.data.company.industry").value("fintech"))
                .andExpect(jsonPath("$.data.company.culture").value("Engineer-led, remote-first."))
                .andExpect(jsonPath("$.data.company.interviewProcess").value("Screen → Tech → HR"))
                .andExpect(jsonPath("$.data.company.sources[0].type").value("user_paste"))
                .andExpect(jsonPath("$.data.company.openRoleCount").value(1))
                .andExpect(jsonPath("$.data.openRoles.length()").value(1))
                .andExpect(jsonPath("$.data.openRoles[0].id").value(mine.path("id").asText()));

        // The positive control the pair needs: the sibling answers with its own single role, so the
        // assertion above is about scoping rather than about a filter that returns nothing.
        mvc.perform(get("/api/v1/companies/" + sibling.path("companyId").asText())
                        .header(authHeader(), "Bearer " + alice))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.company.name").value(siblingName))
                .andExpect(jsonPath("$.data.openRoles.length()").value(1))
                .andExpect(jsonPath("$.data.openRoles[0].id").value(sibling.path("id").asText()));

        // The route now takes the caller -- the roles it answers with carry that caller's match -- so
        // an anonymous read is refused, and an id nobody owns is a 404 rather than an empty profile.
        mvc.perform(get("/api/v1/companies/" + mine.path("companyId").asText()))
                .andExpect(status().isUnauthorized());
        mvc.perform(get("/api/v1/companies/" + UUID.randomUUID())
                        .header(authHeader(), "Bearer " + alice))
                .andExpect(status().isNotFound());
    }

    @Test
    @DisplayName("applications are private and only accept known kanban statuses")
    void applicationsIsolationAndStatus() throws Exception {
        String alice = register("app-" + UUID.randomUUID() + "@example.com");
        String bob = register("app-bob-" + UUID.randomUUID() + "@example.com");

        MvcResult job = mvc.perform(post("/api/v1/jobs")
                        .header(authHeader(), "Bearer " + alice)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(Map.of("title", "Data Engineer",
                                "description", "Build the data platform.",
                                "company", Map.of("name", "Corp" + UUID.randomUUID())))))
                .andExpect(status().isCreated()).andReturn();
        String jobId = dataId(job);

        String appId = dataId(mvc.perform(post("/api/v1/applications")
                        .header(authHeader(), "Bearer " + alice)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(Map.of("jobId", UUID.fromString(jobId),
                                "title", "Data Engineer", "status", "applied"))))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.data.status").value("applied"))
                .andReturn());

        // Bob cannot see or touch it.
        mvc.perform(get("/api/v1/applications/" + appId).header(authHeader(), "Bearer " + bob))
                .andExpect(status().isNotFound());
        mvc.perform(delete("/api/v1/applications/" + appId).header(authHeader(), "Bearer " + bob))
                .andExpect(status().isNotFound());
        mvc.perform(get("/api/v1/applications").header(authHeader(), "Bearer " + bob))
                .andExpect(jsonPath("$.data.total").value(0));

        // Owner can advance status; unknown status is rejected.
        mvc.perform(patch("/api/v1/applications/" + appId).header(authHeader(), "Bearer " + alice)
                        .contentType(MediaType.APPLICATION_JSON).content(json(Map.of("status", "interview"))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.status").value("interview"));
        mvc.perform(patch("/api/v1/applications/" + appId).header(authHeader(), "Bearer " + alice)
                        .contentType(MediaType.APPLICATION_JSON).content(json(Map.of("status", "not-a-status"))))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("INVALID_STATUS"));
    }

    @Test
    @DisplayName("interview sessions and copilot conversations are tenant-scoped")
    void interviewAndConversationIsolation() throws Exception {
        String alice = register("iv-" + UUID.randomUUID() + "@example.com");
        String bob = register("iv-bob-" + UUID.randomUUID() + "@example.com");

        String sessionId = dataId(mvc.perform(post("/api/v1/interview/sessions")
                        .header(authHeader(), "Bearer " + alice)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(Map.of("mode", "backend"))))
                .andExpect(status().isCreated()).andReturn());
        mvc.perform(get("/api/v1/interview/sessions/" + sessionId).header(authHeader(), "Bearer " + bob))
                .andExpect(status().isNotFound());

        MvcResult chat = mvc.perform(post("/api/v1/copilot/chat")
                        .header(authHeader(), "Bearer " + alice)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(Map.of("message", "What should I focus on next?"))))
                .andExpect(status().isOk()).andReturn();
        String convId = MAPPER.readTree(chat.getResponse().getContentAsString())
                .path("data").path("conversationId").asText();
        assertFalse(convId.isBlank());

        mvc.perform(get("/api/v1/conversations/" + convId).header(authHeader(), "Bearer " + alice))
                .andExpect(status().isOk());
        mvc.perform(get("/api/v1/conversations/" + convId).header(authHeader(), "Bearer " + bob))
                .andExpect(status().isNotFound());
        mvc.perform(get("/api/v1/conversations/" + convId + "/messages").header(authHeader(), "Bearer " + bob))
                .andExpect(status().isNotFound());
    }

    @Test
    @DisplayName("knowledge notes are private to their owner")
    void noteIsolation() throws Exception {
        String alice = register("note-" + UUID.randomUUID() + "@example.com");
        String bob = register("note-bob-" + UUID.randomUUID() + "@example.com");

        String noteId = dataId(mvc.perform(post("/api/v1/knowledge/notes")
                        .header(authHeader(), "Bearer " + alice)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(Map.of("title", "Prep", "content", "Study system design"))))
                .andExpect(status().isCreated()).andReturn());

        mvc.perform(get("/api/v1/knowledge/notes").header(authHeader(), "Bearer " + alice))
                .andExpect(jsonPath("$.data.total").value(1));
        mvc.perform(delete("/api/v1/knowledge/notes/" + noteId).header(authHeader(), "Bearer " + bob))
                .andExpect(status().isNotFound());
        mvc.perform(get("/api/v1/knowledge/notes").header(authHeader(), "Bearer " + bob))
                .andExpect(jsonPath("$.data.total").value(0));
    }
}
