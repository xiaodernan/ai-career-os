package com.careeros.network.service;

import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.network.dto.ContactDtos.ContactItem;
import com.careeros.network.dto.ContactDtos.ContactRequest;
import com.careeros.network.entity.Contact;
import com.careeros.network.repository.ContactRepository;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * The registry's CRUD, every query anchored on the caller's id — the list a user sees
 * and the row a user edits are their own by construction, not by a filter the client
 * can forget to send.
 */
@Service
public class ContactService {

    private final ContactRepository contacts;

    public ContactService(ContactRepository contacts) {
        this.contacts = contacts;
    }

    @Transactional(readOnly = true)
    public List<ContactItem> list(UUID userId) {
        return contacts.findByUserIdOrderByUpdatedAtDesc(userId).stream()
                .map(ContactItem::of)
                .toList();
    }

    @Transactional
    public ContactItem create(UUID userId, ContactRequest request) {
        Contact c = new Contact();
        c.setUserId(userId);
        apply(c, request);
        return ContactItem.of(contacts.save(c));
    }

    @Transactional
    public ContactItem update(UUID userId, UUID id, ContactRequest request) {
        Contact c = require(userId, id);
        apply(c, request);
        return ContactItem.of(contacts.save(c));
    }

    @Transactional
    public void delete(UUID userId, UUID id) {
        contacts.delete(require(userId, id));
    }

    private Contact require(UUID userId, UUID id) {
        return contacts.findByIdAndUserId(id, userId)
                .orElseThrow(() -> new ApiException(ApiErrorCode.CONTACT_NOT_FOUND, "Contact not found"));
    }

    private static void apply(Contact c, ContactRequest request) {
        c.setName(request.name().trim());
        c.setRole(blankToNull(request.role()));
        c.setCompany(blankToNull(request.company()));
        c.setRelation(blankToNull(request.relation()));
        c.setEmail(blankToNull(request.email()));
        c.setNotes(blankToNull(request.notes()));
        c.setLastTouchAt(request.lastTouchAt());
    }

    private static String blankToNull(String v) {
        return v == null || v.isBlank() ? null : v.trim();
    }
}
