package com.careeros.ai.web;

import com.careeros.ai.dto.OutreachRequest;
import com.careeros.ai.service.OutreachService;
import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import jakarta.validation.Valid;
import java.util.Map;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * The outreach generator (Epic 11.2).
 *
 * <p>The draft is evidence-bound: the validator strips any skill the profile
 * does not support, so a message can only cite what the candidate can back up.
 */
@RestController
@RequestMapping("/api/v1/outreach")
public class OutreachController {

    private final OutreachService outreach;

    public OutreachController(OutreachService outreach) {
        this.outreach = outreach;
    }

    @PostMapping("/draft")
    public Map<String, Object> draft(@CurrentUser AuthUser user,
                                      @RequestBody @Valid OutreachRequest request) {
        return outreach.draft(user.id(), request);
    }
}
