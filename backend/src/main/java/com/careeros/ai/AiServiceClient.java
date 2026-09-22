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
}
