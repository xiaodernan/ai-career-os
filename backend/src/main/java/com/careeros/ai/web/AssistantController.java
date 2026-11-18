package com.careeros.ai.web;

import com.careeros.ai.dto.NextStepRequest;
import com.careeros.ai.service.AssistantService;
import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import jakarta.validation.Valid;
import java.util.Map;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * The assistant's own surface (Epic 331).
 *
 * <p>The dashboard can ask for one first step; the answer is grounded in the
 * caller's own counts, never in the browser's word. Same discipline as the
 * growth engines: the bridge forwards and owns none of the judgment.
 */
@RestController
@RequestMapping("/api/v1/assistant")
public class AssistantController {

    private final AssistantService assistant;

    public AssistantController(AssistantService assistant) {
        this.assistant = assistant;
    }

    /** Epic 331 — the assistant's one proactive first step. */
    @PostMapping("/next-step")
    public Map<String, Object> nextStep(@CurrentUser AuthUser user,
                                        @RequestBody(required = false)
                                        @Valid NextStepRequest request) {
        return assistant.nextStep(user.id(), request);
    }
}
