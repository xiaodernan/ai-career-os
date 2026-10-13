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

        public final List<String> calls = new ArrayList<>();

        public void reset() {
            failIngest = false;
            queryEmbedding = List.of();
            calls.clear();
        }

        private void record(String name) {
            calls.add(name);
        }

        private void maybeFailIngest() {
            if (failIngest) {
                throw new ApiException(ApiErrorCode.AI_SERVICE_ERROR, "fake ai-service outage");
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
            Map<String, Object> experience = map("company", "Acme Corp",
                    "title", "Backend Engineer",
                    "start", "2021-03",
                    "end", "2024-01",
                    "location", "Shanghai",
                    "bullets", List.of("Led the payments rewrite", "Cut p99 latency by 40%"),
                    "summary", "Distributed systems");
            Map<String, Object> project = map("name", "OpenLedger",
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
                    "company", "FakeCorp",
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
            return map("answer", "Based on your resume, prioritise Kubernetes for this role.",
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
            return map("readiness", map("verdict", "not_ready", "coverage", 0.42),
                    "gap", map("coverage", 0.42, "gaps", List.of()),
                    "salary", map("p25", 300000, "p50", 420000, "p75", 560000, "currency",
                            request.currency() == null ? "CNY" : request.currency()));
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

        private static Map<String, Object> map(Object... kv) {
            Map<String, Object> m = new LinkedHashMap<>();
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
