package com.careeros.notification.web;

import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import com.careeros.notification.dto.NotificationDtos.Inbox;
import com.careeros.notification.dto.NotificationDtos.KeyRequest;
import com.careeros.notification.dto.NotificationDtos.KeysRequest;
import com.careeros.notification.service.NotificationService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * The inbox over HTTP (roadmap 19.3). Every route is scoped to the caller and every write
 * answers with the fresh inbox, so the browser never has to guess what a read or a dismissal
 * did to the list it is showing.
 */
@RestController
@RequestMapping("/api/v1/notifications")
public class NotificationController {

    private final NotificationService notifications;

    public NotificationController(NotificationService notifications) {
        this.notifications = notifications;
    }

    @GetMapping
    public Inbox inbox(@CurrentUser AuthUser user) {
        return notifications.inbox(user.id());
    }

    @PostMapping("/read")
    public Inbox markRead(@CurrentUser AuthUser user, @RequestBody @Valid KeysRequest request) {
        return notifications.markRead(user.id(), request.keys());
    }

    @PostMapping("/read-all")
    public Inbox markAllRead(@CurrentUser AuthUser user) {
        return notifications.markAllRead(user.id());
    }

    @PostMapping("/dismiss")
    public Inbox dismiss(@CurrentUser AuthUser user, @RequestBody @Valid KeyRequest request) {
        return notifications.dismiss(user.id(), request.key());
    }
}
