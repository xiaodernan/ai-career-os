package com.careeros.ai;

import java.util.List;
import java.util.Map;
import java.util.UUID;

/** Internal ai-service endpoints (X-Internal-Token + X-User-Id headers added by the implementation). */
public interface AiServiceClient {

    Map<String, Object> ingestDocument(UUID documentId, UUID userId);

    Map<String, Object> ingestText(UUID userId, String title, String text, String kind, UUID refId);

    Map<String, Object> documentText(UUID documentId, UUID userId);

    Map<String, Object> parseResumeText(String text, UUID userId);

    Map<String, Object> analyzeJd(String rawText, UUID userId);

    Map<String, Object> matchJob(UUID jobId, UUID resumeVersionId, UUID userId);

    Map<String, Object> tailorResume(UUID jobId, UUID resumeVersionId, UUID userId);

    Map<String, Object> coverLetter(UUID jobId, UUID resumeVersionId, String mode,
                                    String previous, String goal, String tone,
                                    String length, UUID userId);

    Map<String, Object> jdSuggestions(UUID resumeVersionId, String jdRaw, UUID userId);

    Map<String, Object> interviewOpening(UUID sessionId, UUID userId);

    Map<String, Object> interviewAnswer(UUID sessionId, String answer, String question,
                                        List<Map<String, Object>> turns, UUID userId);

    Map<String, Object> interviewFinalize(UUID sessionId, List<Map<String, Object>> turns, UUID userId);

    Map<String, Object> copilotChatSync(String message, List<Map<String, Object>> history,
                                        UUID conversationId, Map<String, Object> context, UUID userId);

    /** Starts the same turn as {@link #copilotChatSync} in the background: answers at once with
     * {@code {task_id, run_id}}, and the turn's frames are read off that task's stream. */
    Map<String, Object> copilotChatStart(String message, List<Map<String, Object>> history,
                                         UUID conversationId, Map<String, Object> context, UUID userId);

    /**
     * Embeds one search query so a caller can rank by vector distance in its own SQL.
     * Answers {@code {embedding: [...]}}; an empty list means no provider could answer and the
     * caller must keep its keyword-only ranking rather than fail the search.
     */
    Map<String, Object> embedQuery(String text, UUID userId);

    /**
     * The growth page in one call: readiness + gap + salary + learning plan + progress,
     * composed by the ai-service's 10.8 aggregate so the bridge carries one request and one
     * answer rather than seven round trips. The report's shape is the engine's — this bridge
     * forwards it and owns none of it.
     */
    Map<String, Object> growthReport(
            com.careeros.ai.dto.GrowthReportRequest request, UUID userId);

    /**
     * What the model remembers about this user, newest update first, so a wrong sentence is
     * findable. Answers {@code {items: [...]}}; the rows carry their own id, which is what a
     * correction targets. Unlike the chat pages, this is read through the browser too.
     */
    List<Map<String, Object>> listMemories(List<String> kinds, UUID userId);

    /**
     * Corrects one memory's text and/or its weight. Either may be null — they are corrected
     * independently — and the ai-service answers with the row as it now stands.
     */
    Map<String, Object> patchMemory(UUID memoryId, String content, Double importance, UUID userId);

    /** Forgets one memory. 404 means it was not the caller's, which is also "not there". */
    void deleteMemory(UUID memoryId, UUID userId);

    /**
     * Follow-up reminders for the dashboard tile (11.3): contacts ranked by their
     * relation's cadence, each with a drafted message. Answers `{items: [...]}`.
     */
    List<Map<String, Object>> followUps(UUID userId);

    /**
     * The weekly insight digest (15.3): stalled applications, live stage mix, and
     * headline rates, composed by the ai-service's analytics engine. The engine is
     * a pure function over the caller's application rows, so the backend supplies
     * them — the engine never reads the domain tables itself.
     */
    Map<String, Object> insightDigest(UUID userId, List<Map<String, Object>> applications);

    /**
     * Export all user data as a versioned, hashed bundle (13.1).
     * `sections` carries the rows the BACKEND owns (`applications` and
     * `growth_plans`): the ai-service cannot read them, so the bridge hands
     * them over and the hash is still computed in one place.
     */
    Map<String, Object> exportBundle(UUID userId, boolean anonymized, Map<String, Object> sections);

    /**
     * Plan an idempotent re-import from a bundle (13.2).
     */
    Map<String, Object> importPlan(UUID userId, Map<String, Object> bundle, Map<String, Object> existing);

    /**
     * Redact sections from a bundle before sharing (13.3).
     */
    Map<String, Object> redactBundle(UUID userId, Map<String, Object> bundle, List<String> drop);

    /**
     * Parse a feed (RSS/Atom XML or board-API JSON) into raw postings (14.2).
     * The user id is the caller's: the ingestion runs under their context, so
     * the ai-service can scope anything it writes back to them.
     */
    Map<String, Object> parseFeed(String feed, String source, UUID userId);

    /**
     * Deduplicate postings against the existing corpus (14.3).
     */
    Map<String, Object> dedupeJobs(List<Map<String, Object>> postings, UUID userId);

    /**
     * Freshness sweep: partition postings into fresh / stale / expired / undated (14.3).
     */
    Map<String, Object> freshnessSweep(List<Map<String, Object>> postings, int maxAgeDays,
                                       int staleSeenDays, UUID userId);

    /**
     * One plan for a sweep: create / update / close + within-batch duplicates (14.3).
     */
    Map<String, Object> planIngest(String feed, String source, List<Map<String, Object>> existing,
                                   int maxAgeDays, int staleSeenDays, UUID userId);

    /**
     * Production monitoring (16.1): agent health, cost, and regression detection.
     * The engine is a pure function over the caller's agent runs, so the backend
     * supplies them — the engine never reads the observability tables itself.
     */
    Map<String, Object> healthReport(UUID userId, List<Map<String, Object>> runs);

    /**
     * 12.1 — salary percentiles for a role, by location and seniority band.
     * Deterministic against the seeded corpus; no external data required.
     */
    Map<String, Object> salaryBenchmark(UUID userId, com.careeros.ai.dto.OfferDtos.SalaryRequest request);

    /**
     * 12.2 — the negotiation coach: the offer against the benchmark, with the
     * leverage and the talking points.
     */
    Map<String, Object> negotiate(UUID userId, com.careeros.ai.dto.OfferDtos.NegotiationRequest request);

    /**
     * 12.3 / 12.5 — several offers ranked by total compensation, with the
     * equity grant annualized over its vest.
     */
    Map<String, Object> compareOffers(UUID userId, com.careeros.ai.dto.OfferDtos.CompareOffersRequest request);

    /**
     * 12.4 — the counter-offer draft: a deterministic anchor plus the reasons
     * behind it.
     */
    Map<String, Object> counterOffer(UUID userId, com.careeros.ai.dto.OfferDtos.CounterOfferRequest request);

    /**
     * 10.1 — the distance between the profile and the target role.
     */
    Map<String, Object> gapAnalysis(UUID userId, com.careeros.ai.dto.GrowthEngineRequest request);

    /**
     * 10.7 — target-role readiness, as one verdict.
     */
    Map<String, Object> readiness(UUID userId, com.careeros.ai.dto.GrowthEngineRequest request);

    /**
     * 10.5 — the phased learning plan that closes the gaps.
     */
    Map<String, Object> learningPlan(UUID userId, com.careeros.ai.dto.GrowthEngineRequest request);

    /**
     * 10.9 — which skills the market asks for, counted from the corpus.
     */
    Map<String, Object> skillDemand(UUID userId, com.careeros.ai.dto.GrowthEngineRequest request);

    /**
     * 10.12 — the gaps ranked by importance and by market pull.
     */
    Map<String, Object> learningPriority(UUID userId, com.careeros.ai.dto.GrowthEngineRequest request);

    /**
     * 10.11 — the stepping-stone roles toward a dream role.
     */
    Map<String, Object> progression(UUID userId, com.careeros.ai.dto.GrowthEngineRequest request);

    /**
     * 10.13 — the pre-interview checklist.
     */
    Map<String, Object> interviewPrep(UUID userId, com.careeros.ai.dto.GrowthEngineRequest request);

    /**
     * 6.5 — the STAR story bank, drawn from the profile's own evidence.
     */
    Map<String, Object> storyBank(UUID userId, com.careeros.ai.dto.ProfileEngineRequest request);

    /**
     * 10.10 — the target roles this profile could plausibly aim at.
     */
    Map<String, Object> roleSuggestions(UUID userId, com.careeros.ai.dto.ProfileEngineRequest request);

    /**
     * 10.6 — skill progress between two snapshots. The engine computes the
     * current gap report and diffs it against the previous one the caller holds.
     */
    Map<String, Object> progress(UUID userId, com.careeros.ai.dto.ProgressRequest request);

    /**
     * 11.2 — the outreach message for a real person. Evidence-bound: the
     * validator strips any skill the profile does not support.
     */
    Map<String, Object> outreach(UUID userId, com.careeros.ai.dto.OutreachRequest request);

    /**
     * 15.1 — the pipeline funnel: how many applications reached each stage, and
     * where the leak is.
     */
    Map<String, Object> pipelineFunnel(UUID userId, List<Map<String, Object>> applications);

    /**
     * 15.2 — the reply / interview / offer rates and the per-stage durations.
     * A rejection counts as a response: a no is still an answer.
     */
    Map<String, Object> responseRate(UUID userId, List<Map<String, Object>> applications);

    /**
     * 4.8 — what the corpus says about one company: its roles, its skills, the
     * interview topics the postings name.
     */
    Map<String, Object> companyBrief(UUID userId, com.careeros.ai.dto.CompanyBriefRequest request);
}
