package com.careeros.network.web;

import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import com.careeros.network.dto.ContactDtos.ContactItem;
import com.careeros.network.dto.ContactDtos.ContactRequest;
import com.careeros.network.service.ContactService;
import jakarta.validation.Valid;
import java.util.List;
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
 * The contacts registry over HTTP (roadmap 11.1). A thin CRUD surface: the value of the
 * registry is what the outreach generator and the follow-up cadence read out of it, so
 * the routes do exactly what the user asked and scope every one of them to the caller.
 */
@RestController
@RequestMapping("/api/v1/contacts")
public class ContactController {

    private final ContactService contacts;

    public ContactController(ContactService contacts) {
        this.contacts = contacts;
    }

    @GetMapping
    public List<ContactItem> list(@CurrentUser AuthUser user) {
        return contacts.list(user.id());
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ContactItem create(@CurrentUser AuthUser user,
                              @RequestBody @Valid ContactRequest request) {
        return contacts.create(user.id(), request);
    }

    @PatchMapping("/{id}")
    public ContactItem update(@CurrentUser AuthUser user, @PathVariable UUID id,
                              @RequestBody @Valid ContactRequest request) {
        return contacts.update(user.id(), id, request);
    }

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void delete(@CurrentUser AuthUser user, @PathVariable UUID id) {
        contacts.delete(user.id(), id);
    }
}
