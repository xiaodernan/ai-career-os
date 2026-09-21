package com.careeros.ai;

import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import java.util.UUID;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

@RestController
@RequestMapping("/api/v1/ai")
public class AiStreamController {

    private final SseRelayService relay;

    public AiStreamController(SseRelayService relay) {
        this.relay = relay;
    }

    @GetMapping(value = "/stream/{taskId}", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter stream(@PathVariable UUID taskId, @CurrentUser AuthUser user) {
        return relay.relay(taskId, user.id());
    }
}
