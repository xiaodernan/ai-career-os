package com.careeros.ai.web;

import com.careeros.ai.AiServiceClient;
import com.careeros.ai.dto.RagAnswerRequest;
import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import jakarta.validation.Valid;
import java.util.Map;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Ask a grounded question over the reader's own ingested evidence.
 *
 * <p>The ai-service runs a bounded StateGraph — retrieve → answer (LLM) → verify
 * (deterministic citation check) → render — so the answer's [n] markers can only
 * point at evidence the retrieval actually carried. The engine never quotes a
 * document that is not ready, and a fabricated citation is struck before render.
 * The backend owns no arithmetic here: it forwards the caller's own question under
 * the caller's user id and answers the engine's own shape.
 */
@RestController
@RequestMapping("/api/v1/knowledge")
public class RagAnswerController {

    private final AiServiceClient aiService;

    public RagAnswerController(AiServiceClient aiService) {
        this.aiService = aiService;
    }

    @PostMapping("/answer")
    public Map<String, Object> answer(@CurrentUser AuthUser user,
                                      @RequestBody @Valid RagAnswerRequest request) {
        return aiService.ragAnswer(
                request.query(), request.kinds(), request.documentIds(),
                request.topK(), request.contextSummary(), user.id());
    }
}
