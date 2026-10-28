package com.careeros.report.web;

import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import com.careeros.report.dto.WeeklyDigestDtos.WeeklyDigestDto;
import com.careeros.report.service.WeeklyDigestService;
import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * The weekly letter over HTTP (roadmap 19.4). The list is the caller's own, bounded by the
 * server; composing takes no input -- the week is "now" and the window is the letter's own --
 * and answers the filed letter, so the page never has to guess what it just wrote.
 *
 * <p>There is no route for another user's letter and none for an arbitrary week: a letter is
 * the account's own week, and the scheduler is the only writer that walks everyone.
 */
@RestController
@RequestMapping("/api/v1/digests")
public class WeeklyDigestController {

    private final WeeklyDigestService digests;

    public WeeklyDigestController(WeeklyDigestService digests) {
        this.digests = digests;
    }

    @GetMapping
    public List<WeeklyDigestDto> list(@CurrentUser AuthUser user) {
        return digests.recent(user.id());
    }

    @PostMapping("/run")
    public WeeklyDigestDto composeNow(@CurrentUser AuthUser user) {
        return digests.composeNow(user.id());
    }
}
