package com.careeros.offer.web;

import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import com.careeros.offer.dto.OfferShelfDtos.CounterLetterRequest;
import com.careeros.offer.dto.OfferShelfDtos.CounterLetterResponse;
import com.careeros.offer.dto.OfferShelfDtos.DeleteOfferResponse;
import com.careeros.offer.dto.OfferShelfDtos.OfferItem;
import com.careeros.offer.dto.OfferShelfDtos.OfferLetterRequest;
import com.careeros.offer.dto.OfferShelfDtos.OfferLetterResponse;
import com.careeros.offer.dto.OfferShelfDtos.OfferShelfResponse;
import com.careeros.offer.dto.OfferShelfDtos.UpsertOfferRequest;
import com.careeros.offer.dto.OfferShelfDtos.UpsertOfferResponse;
import com.careeros.offer.service.OfferShelfService;
import jakarta.validation.Valid;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

/**
 * The offer shelf's routes (Epic 185). The path family is shared with the salary
 * actions' controller (12.x) — those are POSTs to named actions, these are the CRUD
 * of the rows they are about, and no verb+path pair collides.
 */
@RestController
@RequestMapping("/api/v1/offers")
public class OfferShelfController {

    private final OfferShelfService shelf;

    public OfferShelfController(OfferShelfService shelf) {
        this.shelf = shelf;
    }

    @GetMapping("/shelf")
    public OfferShelfResponse list(@CurrentUser AuthUser user) {
        return shelf.list(user.id());
    }

    @PostMapping("/shelf")
    @ResponseStatus(HttpStatus.CREATED)
    public UpsertOfferResponse create(@CurrentUser AuthUser user,
                                      @RequestBody @Valid UpsertOfferRequest request) {
        return new UpsertOfferResponse(shelf.create(user.id(), request));
    }

    @PatchMapping("/shelf/{id}")
    public UpsertOfferResponse update(@CurrentUser AuthUser user, @PathVariable UUID id,
                                      @RequestBody @Valid UpsertOfferRequest request) {
        return new UpsertOfferResponse(shelf.update(user.id(), id, request));
    }

    @DeleteMapping("/shelf/{id}")
    public DeleteOfferResponse delete(@CurrentUser AuthUser user, @PathVariable UUID id) {
        return new DeleteOfferResponse(shelf.delete(user.id(), id));
    }

    /** The single row, for the drawer that deep-links from the compare view. */
    @GetMapping("/shelf/{id}")
    public OfferItem get(@CurrentUser AuthUser user, @PathVariable UUID id) {
        return shelf.get(user.id(), id);
    }

    /**
     * The decision letter (Epic 327): the writer addresses the reader about the offer they are
     * holding, grounded in the shelf's own numbers. Always answers; `letter` is null when the
     * ai-service could not keep a grounded one — the honest answer, never a coat of plausibility.
     */
    @PostMapping("/shelf/{id}/letter")
    public OfferLetterResponse letter(@CurrentUser AuthUser user, @PathVariable UUID id,
                                      @RequestBody(required = false) OfferLetterRequest request) {
        String locale = request == null ? null : request.locale();
        return new OfferLetterResponse(shelf.letter(user.id(), id, locale));
    }

    /**
     * The counter-offer letter (Epic 333): the writer drafts the email the reader actually
     * sends about the offer on this shelf — the one that names a gap the table can hear,
     * anchors it in the shelf's own numbers and never an invented one. `letter` is null
     * when nothing grounded survived — the card renders nothing, never a fabricated draft.
     */
    @PostMapping("/shelf/{id}/counter-letter")
    public CounterLetterResponse counterLetter(@CurrentUser AuthUser user,
                                               @PathVariable UUID id,
                                               @RequestBody(required = false) CounterLetterRequest request) {
        String locale = request == null ? null : request.locale();
        return new CounterLetterResponse(shelf.counterLetter(user.id(), id, locale));
    }
}
