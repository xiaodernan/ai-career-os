package com.careeros.support;

import com.careeros.ai.AiServiceClient;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;

/**
 * Deterministic ai-service double for integration tests. Returns contract-shaped payloads so the
 * backend can persist structured rows without ever calling the live service. Tests may flip a flag
 * (e.g. {@link #failIngest}) to exercise AI-outage resilience. Not thread-safe by design: MockMvc
 * tests within a class run sequentially, and each test resets state via {@link #reset()}.
 */
@Configuration
public class FakeAiServiceClientConfig {

    @Bean
    @Primary
    public FakeAiServiceClient fakeAiServiceClient() {
        return new FakeAiServiceClient();
    }

    public static class FakeAiServiceClient implements AiServiceClient {

        /** When true, ingestion/document calls throw to simulate an ai-service outage. */
        public volatile boolean failIngest;

        /**
         * What {@link #embedQuery} answers with: empty means "no provider", so the job search
         * keeps keyword ordering. Tests that exercise hybrid ranking point it at a vector.
         */
        public volatile List<?> queryEmbedding = List.of();

        /**
         * The company name {@link #analyzeJd} reports. Left at the shipped value it changes no
         * test; an import test that has to tell "the analyst named a company the catalog already
         * knew" from "the import created one" needs a name no earlier class filed.
         */
        public volatile String jdCompany = "FakeCorp";

        /**
         * The company {@link #parseResumeText} reports for the parse answer's one experience row.
         * A test that has to prove a re-parse replaced the old rows needs a second value to look
         * for, and a test that has to prove a failed re-parse kept them needs to know which row
         * was the first one's.
         */
        public volatile String resumeExperienceCompany = "Acme Corp";

        /** The project name {@link #parseResumeText} reports, for the same reason as above. */
        public volatile String resumeProjectName = "OpenLedger";

        /**
         * The sentence {@link #copilotChatSync} answers with. A case that needs the answer row
         * refused sets text the database will not take, so the question row is what is left of the
         * turn; the shipped sentence keeps every other case reading the answer it files.
         */
        public volatile String copilotAnswer =
                "Based on your resume, prioritise Kubernetes for this role.";

        public final List<String> calls = new ArrayList<>();

        public void reset() {
            failIngest = false;
            queryEmbedding = List.of();
            jdCompany = "FakeCorp";
            resumeExperienceCompany = "Acme Corp";
            resumeProjectName = "OpenLedger";
            copilotAnswer = "Based on your resume, prioritise Kubernetes for this role.";
            calls.clear();
        }

        private void record(String name) {
            calls.add(name);
        }

        private void maybeFailIngest() {
            if (failIngest) {
                throw new ApiException(ApiErrorCode.AI_SERVICE_UNAVAILABLE, "fake ai-service outage");
            }
        }

        @Override
        public Map<String, Object> ingestDocument(UUID documentId, UUID userId) {
            record("ingestDocument");
            maybeFailIngest();
            return map("task_id", UUID.randomUUID().toString(),
                    "document_id", documentId.toString(),
                    "status", "started");
        }

        @Override
        public Map<String, Object> ingestText(UUID userId, String title, String text, String kind, UUID refId) {
            record("ingestText");
            maybeFailIngest();
            return map("task_id", UUID.randomUUID().toString(),
                    "document_id", UUID.randomUUID().toString(),
                    "source_id", UUID.randomUUID().toString());
        }

        @Override
        public Map<String, Object> documentText(UUID documentId, UUID userId) {
            record("documentText");
            return map("document_id", documentId.toString(),
                    "title", "Ingested document",
                    "status", "ready",
                    "text", "Senior Backend Engineer with 5 years building distributed services.");
        }

        @Override
        public Map<String, Object> parseResumeText(String text, UUID userId) {
            record("parseResumeText");
            Map<String, Object> experience = map("company", resumeExperienceCompany,
                    "title", "Backend Engineer",
                    "start", "2021-03",
                    "end", "2024-01",
                    "location", "Shanghai",
                    "bullets", List.of("Led the payments rewrite", "Cut p99 latency by 40%"),
                    "summary", "Distributed systems");
            Map<String, Object> project = map("name", resumeProjectName,
                    "role", "Author",
                    "period", "2022",
                    "bullets", List.of("Event-sourced ledger"),
                    "tech", List.of("Java", "Postgres"),
                    "url", "https://example.com/openledger");
            Map<String, Object> education = map("school", "Fudan University",
                    "degree", "B.Eng",
                    "field", "Computer Science",
                    "startYear", 2015,
                    "endYear", 2019,
                    "gpa", "3.8",
                    "courses", List.of("Databases", "Operating Systems"));
            Map<String, Object> skill = map("name", "Java", "category", "language", "proficiency", 0.9);
            Map<String, Object> skill2 = map("name", "Postgres", "category", "database", "proficiency", 0.7);
            Map<String, Object> parsed = map("experience", List.of(experience),
                    "projects", List.of(project),
                    "education", List.of(education),
                    "achievements", List.of("Patent holder"),
                    "skills", List.of(skill, skill2));
            Map<String, Object> score = map("total", 78,
                    "detail", map("skills", 80, "impact", 76));
            return map("parsed", parsed, "score", score, "plaintext", text);
        }

        @Override
        public Map<String, Object> analyzeJd(String rawText, UUID userId) {
            record("analyzeJd");
            Map<String, Object> parsed = map("title", "Senior Backend Engineer",
                    "company", jdCompany,
                    "location", "Remote",
                    "experienceYears", 5,
                    "requiredSkills", List.of(map("name", "Java"), map("name", "Kubernetes")),
                    "preferredSkills", List.of(map("name", "Rust")),
                    "responsibilities", List.of("Own services end to end"),
                    "summary", "A senior backend role.");
            return map("parsed", parsed);
        }

        @Override
        public Map<String, Object> matchJob(UUID jobId, UUID resumeVersionId, UUID userId) {
            record("matchJob");
            Map<String, Object> match = map("job_id", jobId.toString(),
                    "overall", 82.5, "technical", 85.0, "experience", 80.0,
                    "projects", 78.0, "education", 90.0,
                    "matched_skills", List.of("Java", "Postgres"),
                    "missing_skills", List.of("Kubernetes", "Rust"),
                    "narrative", "Strong match on core backend skills.");
            return map("match", match,
                    "match_id", UUID.randomUUID().toString(),
                    "jd", map("skills", List.of("Java", "Kubernetes")));
        }

        @Override
        public Map<String, Object> tailorResume(UUID jobId, UUID resumeVersionId, UUID userId) {
            record("tailorResume");
            return map("version_id", UUID.randomUUID().toString(),
                    "plaintext", "Tailored resume body emphasising Kubernetes.",
                    "structured", map("summary", "Kubernetes-focused"),
                    "diff", map("changed", List.of("summary")));
        }

        @Override
        public Map<String, Object> coverLetter(UUID jobId, UUID resumeVersionId, String mode,
                                               String previous, String goal, String tone,
                                               String length, UUID userId) {
            record("coverLetter");
            return map("letter", "Dear hiring manager, I am a great fit.",
                    "mode", mode == null ? "generate" : mode,
                    "tone", tone == null ? "" : tone,
                    "length", length == null ? "" : length);
        }

        @Override
        public Map<String, Object> jdSuggestions(UUID resumeVersionId, String jdRaw, UUID userId) {
            record("jdSuggestions");
            return map("suggestions", List.of(map("type", "keyword", "value", "gRPC")));
        }

        @Override
        public Map<String, Object> interviewOpening(UUID sessionId, UUID userId) {
            record("interviewOpening");
            return map("question", "Tell me about a system you designed that scaled.",
                    "meta", map("topic", "system_design", "depth_level", 0,
                            "expected_points", List.of("tradeoffs", "bottlenecks")));
        }

        @Override
        public Map<String, Object> interviewAnswer(UUID sessionId, String answer, String question,
                                                   List<Map<String, Object>> turns, UUID userId) {
            record("interviewAnswer");
            Map<String, Object> evaluation = map("score", 7.5,
                    "strengths", List.of("clear structure"),
                    "gaps", List.of("shallow on consistency"));
            Map<String, Object> next = map("action", "followup",
                    "question", "How did you handle data consistency during scaling?",
                    "topic", "system_design",
                    "difficulty", 0.65,
                    "reasoning", "Probe the claimed bottleneck fix.");
            return map("evaluation", evaluation, "next", next);
        }

        @Override
        public Map<String, Object> interviewFinalize(UUID sessionId, List<Map<String, Object>> turns, UUID userId) {
            record("interviewFinalize");
            Map<String, Object> evaluation = map("dims", map("technical_accuracy", 8, "communication", 7,
                            "depth", 6),
                    "overall", 7.0,
                    "what_you_did_well", List.of("Clear examples"),
                    "what_was_weak", List.of("Consistency guarantees"),
                    "recommended_study", List.of("Designing Data-Intensive Applications"),
                    "trajectory_detail", List.of(map("depth", 1, "topic", "system_design")));
            return map("evaluation", evaluation);
        }

        @Override
        public Map<String, Object> copilotChatSync(String message, List<Map<String, Object>> history,
                                                   UUID conversationId, Map<String, Object> context, UUID userId) {
            record("copilotChatSync");
            return map("answer", copilotAnswer,
                    "artifacts", List.of(map("type", "checklist", "items", List.of("Add K8s project"))),
                    "sources", List.of(),
                    "actions", List.of(map("type", "open_job", "label", "View matched job")),
                    "run_id", UUID.randomUUID().toString());
        }

        @Override
        public Map<String, Object> copilotChatStart(String message, List<Map<String, Object>> history,
                                                    UUID conversationId, Map<String, Object> context, UUID userId) {
            record("copilotChatStart");
            return map("task_id", UUID.randomUUID().toString(),
                    "run_id", UUID.randomUUID().toString());
        }

        @Override
        public Map<String, Object> embedQuery(String text, UUID userId) {
            record("embedQuery");
            return map("embedding", queryEmbedding);
        }

        /**
         * What the growth-report bridge answers with. The shape is the ai-service engine's —
         * a readiness verdict, a coverage block and a salary band, the three the frontend's
         * growth panel renders first — with enough of it for the controller tests to pin the
         * pass-through and nothing else.
         */
        @Override
        public Map<String, Object> growthReport(com.careeros.ai.dto.GrowthReportRequest request,
                                                UUID userId) {
            record("growthReport");
            // The diff is the engine's own rule: a run with no previous in the request is a
            // baseline, which is exactly how the service feeds the stored gap block through.
            return map("readiness", map("verdict", "not_ready", "coverage", 0.42),
                    "gap", map("coverage", 0.42, "gaps", List.of()),
                    "salary", map("p25", 300000, "p50", 420000, "p75", 560000, "currency",
                            request.currency() == null ? "CNY" : request.currency()),
                    "progress", map("baseline", request.previous() == null));
        }

        /**
         * What the memory routes answer. Non-empty means the ai-service has some to correct;
         * empty is the honest "the extractor has written nothing yet".
         */
        public volatile List<Map<String, Object>> memories = new ArrayList<>();

        @Override
        public List<Map<String, Object>> listMemories(List<String> kinds, UUID userId) {
            record("listMemories");
            List<Map<String, Object>> rows = memories;
            if (kinds == null || kinds.isEmpty()) {
                return rows;
            }
            return rows.stream()
                    .filter(r -> kinds.contains(r.get("kind")))
                    .collect(java.util.stream.Collectors.toList());
        }

        @Override
        public Map<String, Object> patchMemory(UUID memoryId, String content, Double importance,
                                               UUID userId) {
            record("patchMemory");
            return map("id", memoryId == null ? null : memoryId.toString(),
                    "kind", "skill", "key", "kafka",
                    "content", content == null ? "unchanged" : content,
                    "importance", importance == null ? 0.6 : importance,
                    "source", "conversation",
                    "createdAt", null, "updatedAt", null);
        }

        @Override
        public void deleteMemory(UUID memoryId, UUID userId) {
            record("deleteMemory");
        }

        /**
         * What the follow-up reminder bridge answers with (11.3): one contact past its
         * relation's cadence, with the engine's own drafted message.
         */
        @Override
        public List<Map<String, Object>> followUps(UUID userId) {
            record("followUps");
            return List.of(map("id", UUID.randomUUID().toString(),
                    "name", "Alex Chen", "company", "FakeCorp", "relation", "recruiter",
                    "priority", "overdue", "days_since", 45, "cadence_days", 30,
                    "suggested_message", "Hi Alex, hope things are going well at FakeCorp."));
        }

        /**
         * What the insight-digest bridge answers with (15.3): the engine's own stalled
         * list, stage mix and headline rates.
         *
         * The mix is a distribution, not the funnel: three applications sit at three
         * positions and the counts add up to {@code totalApplications}. Positions nobody
         * is sitting at are absent rather than zeroed, which is what the engine emits.
         */
        @Override
        public Map<String, Object> insightDigest(UUID userId, List<Map<String, Object>> applications,
                                                 String locale) {
            record("insightDigest");
            return map("generatedAt", "2026-10-20T00:00:00+00:00",
                    "windowDays", 14,
                    "totalApplications", 3,
                    "activePipeline", 2,
                    "stageCounts", map("saved", 1, "applied", 1, "oa", 1),
                    "responseRate", 0.5,
                    "offerRate", 0.0,
                    "stalledCount", 1,
                    "stalled", List.of(map("id", UUID.randomUUID().toString(),
                            "title", "Backend Engineer", "company", "FakeCorp",
                            "status", "applied", "daysSinceLastActivity", 30)),
                    "signals", List.of("1 application(s) have gone quiet past 14 days."));
        }

        /**
         * What the export bridge answers with (13.1): a bundle whose manifest carries
         * the content hash the redaction path recomputes.
         */
        @Override
        public Map<String, Object> exportBundle(UUID userId, boolean anonymized,
                                                Map<String, Object> sections) {
            record("exportBundle");
            Map<String, Object> data = new LinkedHashMap<>();
            data.put("profile", map("id", userId.toString()));
            data.put("resumes", List.of());
            data.put("knowledge", List.of());
            data.put("job_descriptions", List.of());
            data.put("interviews", List.of());
            data.put("memories", List.of());
            // The backend's own sections travel in the bundle too -- that is what
            // makes an export complete rather than a reading list.
            data.put("applications", sections == null ? List.of() : sections.get("applications"));
            data.put("growth_plans", sections == null ? List.of() : sections.get("growth_plans"));
            return map("schema_version", "1.1.0",
                    "generator", "ai-career-os",
                    "generated_at", "2026-10-20T00:00:00+00:00",
                    "user", map("id", userId.toString(), "anonymized", anonymized),
                    "manifest", map("schema_version", "1.1.0", "generator", "ai-career-os",
                            "counts", map("profile", 1, "resumes", 0, "knowledge", 0,
                                    "job_descriptions", 0, "interviews", 0, "memories", 0,
                                    "applications", 0, "growth_plans", 0),
                            "content_hash", "fake-hash", "anonymized", anonymized),
                    "data", data);
        }

        @Override
        public Map<String, Object> importPlan(UUID userId, Map<String, Object> bundle,
                                               Map<String, Object> existing) {
            record("importPlan");
            return map("schema_version", "1.0.0",
                    "source_content_hash", "fake-hash",
                    "sections", map("profile", List.of(map("op", "update", "id", userId.toString(),
                            "content_hash", "fake-hash"))),
                    "op_counts", map("create", 0, "update", 1, "delete", 0, "total", 1));
        }

        @Override
        public Map<String, Object> redactBundle(UUID userId, Map<String, Object> bundle,
                                                 List<String> drop) {
            record("redactBundle");
            return map("schema_version", "1.0.0",
                    "generator", "ai-career-os",
                    "generated_at", "2026-10-20T00:00:00+00:00",
                    "user", map("id", userId.toString(), "anonymized", false),
                    "manifest", map("schema_version", "1.0.0", "generator", "ai-career-os",
                            "counts", map("profile", 1, "resumes", 0, "knowledge", 0,
                                    "job_descriptions", 0, "interviews", 0, "memories", 0),
                            "content_hash", "fake-hash", "anonymized", false,
                            "redacted_sections", drop == null ? List.of() : drop),
                    "data", map("profile", map("id", userId.toString())));
        }

        /**
         * What the render answers with (13.1): a self-contained, print-ready
         * document. The PDF half is the optional converter's, so the double
         * answers the HTML.
         */
        @Override
        public Map<String, Object> renderBundle(UUID userId, Map<String, Object> bundle, String format) {
            record("renderBundle");
            return map("format", format == null || format.isBlank() ? "html" : format,
                    "html", "<!doctype html><html lang=\"zh\"><body><h1>AI Career OS — 数据导出</h1></body></html>");
        }

        /** 19.5 -- one version's print-ready document, answered as the renderer would. */
        @Override
        public Map<String, Object> renderResume(UUID userId, Map<String, Object> resume, String text,
                                                String title, String subtitle, String locale) {
            record("renderResume");
            return map("format", "html",
                    "html", "<!doctype html><html lang=\"en\"><body><h1>" + title + "</h1></body></html>");
        }

        /**
         * What the memory restore answers with (13.2): the rows the ai-service
         * upserted on (kind, key).
         */
        @Override
        public Map<String, Object> importMemories(UUID userId, List<Map<String, Object>> memories) {
            record("importMemories");
            return map("imported", memories == null ? 0 : memories.size(), "skipped", 0);
        }

        @Override
        public Map<String, Object> parseFeed(String feed, String source, UUID userId) {
            record("parseFeed");
            return map("postings", List.of(map("title", "Backend Engineer", "company", "FakeCorp",
                    "location", "Shanghai", "source", source)), "count", 1);
        }

        @Override
        public Map<String, Object> dedupeJobs(List<Map<String, Object>> postings, UUID userId) {
            record("dedupeJobs");
            return map("unique", postings == null ? List.of() : postings,
                    "duplicates", List.of(),
                    "inputCount", postings == null ? 0 : postings.size(),
                    "uniqueCount", postings == null ? 0 : postings.size(),
                    "duplicateCount", 0);
        }

        @Override
        public Map<String, Object> freshnessSweep(List<Map<String, Object>> postings, int maxAgeDays,
                                                   int staleSeenDays, UUID userId) {
            record("freshnessSweep");
            return map("fresh", postings == null ? List.of() : postings,
                    "stale", List.of(), "expired", List.of(), "undated", List.of(),
                    "counts", map("fresh", postings == null ? 0 : postings.size(),
                            "stale", 0, "expired", 0, "undated", 0));
        }

        @Override
        public Map<String, Object> planIngest(String feed, String source,
                                               List<Map<String, Object>> existing,
                                               int maxAgeDays, int staleSeenDays, UUID userId) {
            record("planIngest");
            return map("source", source,
                    "create", List.of(), "update", List.of(), "close", List.of(),
                    "duplicates", List.of(),
                    "counts", map("incoming", 0, "create", 0, "update", 0, "close", 0, "duplicates", 0));
        }

        /**
         * What the health-report bridge answers with (16.1): the engine's own verdict,
         * error rate, cost and latency figures.
         */
        @Override
        public Map<String, Object> healthReport(UUID userId, List<Map<String, Object>> runs) {
            record("healthReport");
            return map("verdict", "healthy",
                    "errorRate", 0.0,
                    "totalRuns", 12,
                    "totalCostUsd", 0.42,
                    "totalTokens", 8400,
                    "p50LatencyMs", 1200,
                    "p95LatencyMs", 3100,
                    "alerts", List.of(),
                    "regressions", List.of());
        }

        /**
         * What the salary benchmark answers with (12.1): the engine's own percentiles
         * and sample size.
         */
        @Override
        public Map<String, Object> salaryBenchmark(UUID userId,
                                                   com.careeros.ai.dto.OfferDtos.SalaryRequest request) {
            record("salaryBenchmark");
            return map("role", request.role(),
                    "sampleSize", 8,
                    "percentiles", map("p25", 300000, "p50", 420000, "p75", 560000),
                    "currency", request.currency() == null ? "CNY" : request.currency());
        }

        /**
         * What the negotiation coach answers with (12.2): the verdict, the leverage
         * and the talking points.
         */
        @Override
        public Map<String, Object> negotiate(UUID userId,
                                             com.careeros.ai.dto.OfferDtos.NegotiationRequest request) {
            record("negotiate");
            return map("verdict", "below_market",
                    "offerBase", request.offerBase(),
                    "benchmark", map("p50", 420000),
                    "leverage", "Your match score is strong; anchor above the median.",
                    "talkingPoints", List.of("Lead with the projects that match the role."));
        }

        /**
         * What the offer comparison answers with (12.3 / 12.5): the engine's own
         * rows and its pick.
         */
        @Override
        public Map<String, Object> compareOffers(UUID userId,
                                                  com.careeros.ai.dto.OfferDtos.CompareOffersRequest request) {
            record("compareOffers");
            List<Map<String, Object>> rows = new ArrayList<>();
            for (var offer : request.offers()) {
                rows.add(map("label", offer.label(), "base", offer.base(), "bonus", offer.bonus(),
                        "firstYearCash", offer.base() + offer.bonus(),
                        "annualEquity", 0, "totalComp", offer.base() + offer.bonus()));
            }
            return map("rows", rows, "best", rows.isEmpty() ? null : rows.get(0),
                    "notes", List.of());
        }

        /**
         * What the counter-offer draft answers with (12.4): the anchor and the
         * reasons behind it.
         */
        @Override
        public Map<String, Object> counterOffer(UUID userId,
                                                 com.careeros.ai.dto.OfferDtos.CounterOfferRequest request) {
            record("counterOffer");
            return map("anchor", 480000,
                    "reasons", List.of("Your match score clears the bar for this band."),
                    "script", "Based on the scope of the role and my experience, I would like to discuss a base of 480000.");
        }

        /**
         * What the granular growth engines answer with. Each is the engine's own
         * shape; the doubles carry enough for the controller tests to pin the
         * pass-through and nothing else.
         */
        @Override
        public Map<String, Object> gapAnalysis(UUID userId,
                                               com.careeros.ai.dto.GrowthEngineRequest request) {
            record("gapAnalysis");
            return map("targetRole", request.targetRole(), "coverage", 0.42,
                    "gaps", List.of(map("name", "Kubernetes", "importance", "must")));
        }

        @Override
        public Map<String, Object> readiness(UUID userId,
                                              com.careeros.ai.dto.GrowthEngineRequest request) {
            record("readiness");
            return map("verdict", "not_ready", "coverage", 0.42, "gapCount", 3,
                    "coveredCount", 5, "blockers", List.of("Kubernetes"));
        }

        @Override
        public Map<String, Object> learningPlan(UUID userId,
                                                com.careeros.ai.dto.GrowthEngineRequest request) {
            record("learningPlan");
            return map("phases", List.of(map("phase", "foundation", "label", "Foundation",
                    "items", List.of(map("topic", "Kubernetes basics", "priority", "must")))));
        }

        @Override
        public Map<String, Object> skillDemand(UUID userId,
                                                com.careeros.ai.dto.GrowthEngineRequest request) {
            record("skillDemand");
            return map("skills", List.of(map("name", "Kubernetes", "count", 12)));
        }

        @Override
        public Map<String, Object> learningPriority(UUID userId,
                                                     com.careeros.ai.dto.GrowthEngineRequest request) {
            record("learningPriority");
            return map("priorities", List.of(map("skill", "Kubernetes", "priority", "must",
                    "marketDemand", 12)));
        }

        @Override
        public Map<String, Object> progression(UUID userId,
                                                com.careeros.ai.dto.GrowthEngineRequest request) {
            record("progression");
            return map("steps", List.of(map("role", "Platform Engineer", "reachable", true)),
                    "missing", List.of("Kubernetes"));
        }

        @Override
        public Map<String, Object> interviewPrep(UUID userId,
                                                 com.careeros.ai.dto.GrowthEngineRequest request) {
            record("interviewPrep");
            return map("study", List.of(map("topic", "Kubernetes", "why", "It is a gap.")),
                    "rehearse", List.of(map("topic", "Distributed systems")),
                    "likelyTopics", List.of("Scaling"));
        }

        @Override
        public Map<String, Object> storyBank(UUID userId,
                                              com.careeros.ai.dto.ProfileEngineRequest request) {
            record("storyBank");
            return map("stories", List.of(map("title", "Payments rewrite",
                    "evidence", "Led the payments rewrite")));
        }

        @Override
        public Map<String, Object> roleSuggestions(UUID userId,
                                                    com.careeros.ai.dto.ProfileEngineRequest request) {
            record("roleSuggestions");
            return map("roles", List.of(map("role", "Senior Backend Engineer", "score", 0.8)));
        }

        @Override
        public Map<String, Object> progress(UUID userId,
                                             com.careeros.ai.dto.ProgressRequest request) {
            record("progress");
            return map("baseline", request.previous() == null,
                    "closed", List.of(), "improved", List.of(), "regressed", List.of(),
                    "stillOpen", List.of(),
                    "previousCoverage", 0.42, "currentCoverage", 0.5, "delta", 0.08);
        }

        /**
         * What the outreach generator answers with (11.2): the message and the
         * evidence it cited.
         */
        @Override
        public Map<String, Object> outreach(UUID userId,
                                             com.careeros.ai.dto.OutreachRequest request) {
            record("outreach");
            return map("message", "Hi " + request.name() + " — hope you've been well.",
                    "purpose", request.purpose() == null ? "referral" : request.purpose(),
                    "sources", List.of());
        }

        /**
         * What the pipeline funnel answers with (15.1): the stage counts and the
         * conversion at each step.
         */
        @Override
        public Map<String, Object> pipelineFunnel(UUID userId,
                                                    List<Map<String, Object>> applications) {
            record("pipelineFunnel");
            return map("pipeline", List.of(
                    map("stage", "applied", "count", 2, "conversionFromApplied", 1.0),
                    map("stage", "oa", "count", 1, "conversionFromApplied", 0.5)),
                    "appliedCount", 2, "savedCount", 0, "rejectedCount", 0,
                    "totalApplications", applications == null ? 0 : applications.size());
        }

        /**
         * What the response rate answers with (15.2): the rates and the
         * per-stage durations.
         */
        @Override
        public Map<String, Object> responseRate(UUID userId,
                                                 List<Map<String, Object>> applications) {
            record("responseRate");
            return map("appliedCount", 2, "respondedCount", 1, "responseRate", 0.5,
                    "offerCount", 0, "offerRate", 0.0,
                    "interviewCount", 0, "interviewRate", 0.0, "timeInStage", Map.of());
        }

        /**
         * What the company brief answers with (4.8): the corpus's own rows for
         * one company.
         */
        @Override
        public Map<String, Object> companyBrief(UUID userId,
                                                 com.careeros.ai.dto.CompanyBriefRequest request) {
            record("companyBrief");
            return map("company", request.company(),
                    "roles", List.of(map("title", "Backend Engineer", "location", "Shanghai")),
                    "skills", List.of(map("name", "Java", "count", 4)),
                    "interviewTopics", List.of("System design"));
        }

        private static Map<String, Object> map(Object... kv) {            Map<String, Object> m = new LinkedHashMap<>();
            for (int i = 0; i < kv.length; i += 2) {
                m.put(String.valueOf(kv[i]), kv[i + 1]);
            }
            return m;
        }

        /** Exposed for tests that assert call ordering. */
        public Map<String, Object> empty() {
            return new HashMap<>();
        }
    }
}
