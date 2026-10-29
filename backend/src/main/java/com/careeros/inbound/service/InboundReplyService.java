package com.careeros.inbound.service;

import com.careeros.application.entity.Application;
import com.careeros.application.entity.ApplicationEvent;
import com.careeros.application.repository.ApplicationEventRepository;
import com.careeros.application.repository.ApplicationRepository;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.common.PageDTO;
import com.careeros.inbound.dto.InboundMailDtos.InboundMailItem;
import com.careeros.inbound.entity.InboundMail;
import com.careeros.inbound.repository.InboundMailRepository;
import java.time.OffsetDateTime;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * The reply meets the application (roadmap 37.3).
 *
 * <p>A letter is read on arrival, and this service decides which card it answers -- or that no
 * card can be named yet. The match is deliberately narrow: the employer's name, case aside,
 * must equal the application's company, and when a reader has more than one application at
 * that employer the letter's role must pick out exactly one title. A guess that narrows to
 * nothing files nothing, because a reply on the wrong card is worse than a reply waiting.
 *
 * <p>Filing is two writes in one transaction: the letter remembers the application, and the
 * application's timeline gains a {@code reply} event carrying the mail id, sender, subject and
 * intent. The event is what makes the letter part of the card's story; the reader's inbox
 * reads the letter itself, so no notification row is written (the inbox synthesises episodes).
 *
 * <p>The intent suggests a stage -- a rejection suggests {@code rejected}, an interview
 * {@code interview}, an offer {@code offer} -- but nothing here moves the application. The
 * suggestion is answered on the wire and applied only by the reader's own explicit write, on
 * the application the letter is actually filed on.
 */
@Service
public class InboundReplyService {

    /** The timeline event a filed letter writes; the reader's board renders it. */
    public static final String EVENT_REPLY = "reply";

    /** The five readings the engine answers with; a stage is suggested for three of them. */
    private static final Map<String, String> SUGGESTED_STAGE = Map.of(
            "rejection", "rejected",
            "interview", "interview",
            "offer", "offer");

    private final InboundMailRepository mails;
    private final ApplicationRepository applications;
    private final ApplicationEventRepository events;

    public InboundReplyService(InboundMailRepository mails, ApplicationRepository applications,
                               ApplicationEventRepository events) {
        this.mails = mails;
        this.applications = applications;
        this.events = events;
    }

    /** The replies page: one account's letters newest first, each with what it is filed on. */
    @Transactional(readOnly = true)
    public PageDTO<InboundMailItem> list(UUID userId, Pageable pageable) {
        Page<InboundMail> page = mails.findByUserIdOrderByReceivedAtDescIdDesc(userId, pageable);
        Map<UUID, Application> byId = applicationsOf(userId, page.getContent());
        return PageDTO.from(page, mail -> item(mail, byId.get(mail.getApplicationId())));
    }

    /**
     * Files one letter on the application the reader chose. A letter already on that same card
     * answers the card unchanged, so a double click is not an error; a letter already on a
     * different card is refused rather than moved, because a reply answers one application and
     * its timeline row has already said so.
     */
    @Transactional
    public InboundMailItem file(UUID userId, UUID mailId, UUID applicationId) {
        InboundMail mail = mails.findByIdAndUserId(mailId, userId)
                .orElseThrow(() -> new ApiException(ApiErrorCode.INBOUND_MAIL_NOT_FOUND,
                        "Reply not found"));
        Application app = applications.findByIdAndUserId(applicationId, userId)
                .orElseThrow(() -> new ApiException(ApiErrorCode.APPLICATION_NOT_FOUND,
                        "Application not found"));
        if (mail.getApplicationId() != null) {
            if (mail.getApplicationId().equals(app.getId())) {
                return item(mail, app);
            }
            throw new ApiException(ApiErrorCode.INBOUND_MAIL_ALREADY_FILED,
                    "This reply is already filed on another application");
        }
        fileOn(mail, app);
        return item(mail, app);
    }

    /**
     * Files a freshly read letter on the one card its company and role name, if they name one.
     * Answers whether a card was found; an unmatched letter stays where the replies page can
     * show it. Called from the webhook's own path, after the letter and its reading are stored.
     */
    @Transactional
    public boolean autoFile(InboundMail mail) {
        if (mail == null || mail.getApplicationId() != null) {
            return false;
        }
        String company = trimmed(mail.getCompany());
        if (company == null) {
            return false;
        }
        Application app = match(mail.getUserId(), company, mail.getRole());
        if (app == null) {
            return false;
        }
        fileOn(mail, app);
        return true;
    }

    /** The one application a company names, narrowed by role containment when it names several. */
    private Application match(UUID userId, String company, String role) {
        List<Application> named = applications.findByUserIdAndCompanyNameIgnoreCase(userId, company);
        if (named.size() == 1) {
            return named.get(0);
        }
        String needle = trimmed(role);
        if (needle == null) {
            return null;
        }
        String low = needle.toLowerCase(Locale.ROOT);
        List<Application> narrowed = named.stream()
                .filter(app -> app.getTitle() != null
                        && app.getTitle().toLowerCase(Locale.ROOT).contains(low))
                .toList();
        return narrowed.size() == 1 ? narrowed.get(0) : null;
    }

    private void fileOn(InboundMail mail, Application app) {
        mail.setApplicationId(app.getId());
        mail.setFiledAt(OffsetDateTime.now());
        mails.save(mail);

        ApplicationEvent event = new ApplicationEvent();
        event.setApplicationId(app.getId());
        event.setUserId(mail.getUserId());
        event.setKind(EVENT_REPLY);
        event.setPayload(payloadOf(mail));
        events.save(event);
    }

    /** The timeline's view of the letter: whose it was, what it said, and what it was read as. */
    private static Map<String, Object> payloadOf(InboundMail mail) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("mail_id", mail.getId().toString());
        payload.put("sender", mail.getFromAddress());
        payload.put("subject", mail.getSubject());
        if (mail.getIntent() != null) {
            payload.put("intent", mail.getIntent());
        }
        return payload;
    }

    private Map<UUID, Application> applicationsOf(UUID userId, List<InboundMail> mails) {
        Set<UUID> ids = mails.stream()
                .map(InboundMail::getApplicationId)
                .filter(Objects::nonNull)
                .collect(Collectors.toSet());
        if (ids.isEmpty()) {
            return Map.of();
        }
        Map<UUID, Application> out = new HashMap<>();
        for (Application app : applications.findAllById(ids)) {
            if (userId.equals(app.getUserId())) {
                out.put(app.getId(), app);
            }
        }
        return out;
    }

    static InboundMailItem item(InboundMail mail, Application app) {
        return new InboundMailItem(mail.getId(), mail.getFromAddress(), mail.getSubject(),
                mail.getBodyText(), mail.getIntent(), mail.getCompany(), mail.getRole(),
                suggestedStage(mail.getIntent()), mail.getApplicationId(),
                app == null ? null : app.getTitle(), mail.getReceivedAt(), mail.getFiledAt());
    }

    /**
     * The stage a reading suggests, in the board's own vocabulary, or null when it suggests
     * none. This is the only place the mapping lives, so the replies page and the timeline
     * cannot disagree about what a rejection means.
     */
    public static String suggestedStage(String intent) {
        return intent == null ? null : SUGGESTED_STAGE.get(intent);
    }

    private static String trimmed(String value) {
        if (value == null) {
            return null;
        }
        String text = value.strip();
        return text.isEmpty() ? null : text;
    }
}
