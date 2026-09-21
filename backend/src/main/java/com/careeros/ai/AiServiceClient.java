package com.careeros.ai;

import java.util.UUID;

/** Internal ai-service endpoints. Grow this surface as domain modules land. */
public interface AiServiceClient {

    record IngestResult(UUID taskId, String status) {
    }

    record ResumeParseResult(UUID taskId, String status) {
    }

    IngestResult ingestDocument(UUID documentId, UUID userId);

    ResumeParseResult parseResume(UUID resumeId, UUID userId);
}
