package com.careeros.push.web;

import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import com.careeros.push.dto.PushDtos.PushSubscriptionItem;
import com.careeros.push.dto.PushDtos.PushSubscriptionRequest;
import com.careeros.push.service.PushSubscriptionService;
import jakarta.validation.Valid;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

/**
 * The account's push addresses over HTTP (roadmap 33.1). Every route is scoped to the caller:
 * a browser registration rings the reader who last opted in there, and one account's devices
 * are never another's to list or forget. Registering answers 200 rather than 201 because a
 * re-subscribe is the common case and creates nothing.
 */
@RestController
@RequestMapping("/api/v1/push/subscriptions")
public class PushSubscriptionController {

    private final PushSubscriptionService subscriptions;

    public PushSubscriptionController(PushSubscriptionService subscriptions) {
        this.subscriptions = subscriptions;
    }

    @GetMapping
    public List<PushSubscriptionItem> list(@CurrentUser AuthUser user) {
        return subscriptions.list(user.id());
    }

    @PostMapping
    public PushSubscriptionItem register(@CurrentUser AuthUser user,
            @RequestBody @Valid PushSubscriptionRequest request) {
        return subscriptions.register(user.id(), request);
    }

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void delete(@CurrentUser AuthUser user, @PathVariable UUID id) {
        subscriptions.delete(user.id(), id);
    }

    @DeleteMapping
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void deleteAll(@CurrentUser AuthUser user) {
        subscriptions.deleteAll(user.id());
    }
}
