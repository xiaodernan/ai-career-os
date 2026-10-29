package com.careeros.calendar.web;

import com.careeros.auth.entity.User;
import com.careeros.auth.repository.UserRepository;
import com.careeros.calendar.service.CalendarLinks;
import com.careeros.calendar.service.CalendarService;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import java.nio.charset.StandardCharsets;
import java.util.UUID;
import org.springframework.http.CacheControl;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * The calendar feed (roadmap 34), in both directions.
 *
 * <p>{@code GET /calendar/link} is the signed-in half: the settings screen asks the account
 * for its own subscription address. {@code GET /calendar.ics?token=...} is the anonymous
 * half: a calendar client fetches it from a server that cannot log in, so the token is the
 * credential and the answer is the document itself, not an envelope. An unreadable token,
 * another account's signature, a retired secret and a deleted account are one 404 with the
 * same sentence -- telling a forger which half was wrong would grade their guesses.
 *
 * <p>The document is {@code no-store} and {@code noindex}: it names the reader's applications
 * and the companies they are talking to. Past reminders are kept, because the calendar is a
 * mirror of the board rather than a list of what is still ahead.
 */
@RestController
@RequestMapping("/api/v1")
public class CalendarController {

    private static final MediaType CALENDAR = MediaType.parseMediaType("text/calendar;charset=UTF-8");
    private static final String NO_LINK = "This calendar link is not valid or has been retired";

    private final CalendarLinks links;
    private final CalendarService calendar;
    private final UserRepository users;

    public CalendarController(CalendarLinks links, CalendarService calendar, UserRepository users) {
        this.links = links;
        this.calendar = calendar;
        this.users = users;
    }

    /** The account's own subscription address, for the settings card to show and copy. */
    @GetMapping("/calendar/link")
    public CalendarLink link(@CurrentUser AuthUser user) {
        return new CalendarLink(links.feed(user.id()));
    }

    /** The document a calendar client subscribes to; the token names and proves the account. */
    @GetMapping(value = "/calendar.ics", produces = "text/calendar")
    public ResponseEntity<byte[]> feed(
            @RequestParam(value = "token", required = false) String token) {
        UUID userId = links.account(token);
        if (userId == null) {
            throw new ApiException(ApiErrorCode.CALENDAR_LINK_INVALID, NO_LINK);
        }
        User account = users.findById(userId)
                .orElseThrow(() -> new ApiException(ApiErrorCode.CALENDAR_LINK_INVALID, NO_LINK));
        byte[] body = calendar.feed(userId, account.getLocale()).getBytes(StandardCharsets.UTF_8);
        return ResponseEntity.ok()
                .contentType(CALENDAR)
                .cacheControl(CacheControl.noStore())
                .header("X-Robots-Tag", "noindex")
                .body(body);
    }

    /** The answer key the settings card reads; adding the calendar later needs no second route. */
    public record CalendarLink(String url) {
    }
}
