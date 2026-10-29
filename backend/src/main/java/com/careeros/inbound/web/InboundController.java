package com.careeros.inbound.web;

import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import com.careeros.common.PageDTO;
import com.careeros.common.Paging;
import com.careeros.inbound.dto.InboundMailDtos.FileRequest;
import com.careeros.inbound.dto.InboundMailDtos.InboundMailItem;
import com.careeros.inbound.service.InboundLinks;
import com.careeros.inbound.service.InboundMailService;
import com.careeros.inbound.service.InboundReplyService;
import com.fasterxml.jackson.databind.JsonNode;
import jakarta.validation.Valid;
import java.util.UUID;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * The reply's two doors (roadmap 37.1), and the reader's side of them (37.3).
 *
 * <p>{@code GET /inbound/link} is the signed-in half: the settings card asks the account for
 * the address a provider should forward to, and on a deployment that has not configured a
 * receiving domain it is told so instead of being handed one that bounces. {@code
 * POST /inbound/mail/{token}} is the anonymous half: a mail provider posts one letter to the
 * address it was given, and the token in the local part is the credential. Both halves are
 * metered per token by the rate limiter, so a leaked address cannot be used to fill a row
 * with junk faster than a post office could deliver it.
 *
 * <p>The webhook answers the same body for a first delivery and a retry. The provider only
 * needs to know the letter was taken; which attempt wrote the row is the server's business,
 * and a different answer per attempt would invite the provider to redeliver forever.
 *
 * <p>{@code GET /inbound/mails} and {@code POST /inbound/mails/{id}/file} are the reader's:
 * the letters one account received, newest first, and the one write that ties a letter to the
 * card it answers. Only the signed-in account's own letters are listed or filed -- another
 * account's letter id is the same 404 as a letter that never existed.
 */
@RestController
@RequestMapping("/api/v1/inbound")
public class InboundController {

    private final InboundLinks links;
    private final InboundMailService mail;
    private final InboundReplyService replies;

    public InboundController(InboundLinks links, InboundMailService mail,
                             InboundReplyService replies) {
        this.links = links;
        this.mail = mail;
        this.replies = replies;
    }

    /** The account's own forwarding address, for the settings card to show and copy. */
    @GetMapping("/link")
    public InboundAddress link(@CurrentUser AuthUser user) {
        if (!links.configured()) {
            throw new ApiException(ApiErrorCode.INBOUND_NOT_CONFIGURED,
                    "Inbound mail is not configured on this deployment");
        }
        return new InboundAddress(links.address(user.id()));
    }

    /** The provider's one route: a letter, acknowledged whether it is new or a retry. */
    @PostMapping("/mail/{token}")
    public Acknowledgement receive(@PathVariable("token") String token,
                                   @RequestBody(required = false) JsonNode body) {
        mail.receive(token, InboundMailPayload.fromPostmark(body));
        return new Acknowledgement("received");
    }

    /** The replies page: the account's letters newest first, filed or waiting. */
    @GetMapping("/mails")
    public PageDTO<InboundMailItem> list(@CurrentUser AuthUser user,
                                         @RequestParam(defaultValue = "0") int page,
                                         @RequestParam(defaultValue = "50") int size) {
        return replies.list(user.id(), Paging.of(page, size).pageable());
    }

    /** Ties one waiting letter to the card it answers; a double click on the same card is a no-op. */
    @PostMapping("/mails/{id}/file")
    public InboundMailItem file(@CurrentUser AuthUser user, @PathVariable("id") UUID id,
                                @RequestBody @Valid FileRequest request) {
        return replies.file(user.id(), id, request.applicationId());
    }

    /** The answer key the settings card reads. */
    public record InboundAddress(String address) {
    }

    /** What a mail provider sees; it names no account and no letter. */
    public record Acknowledgement(String status) {
    }
}
