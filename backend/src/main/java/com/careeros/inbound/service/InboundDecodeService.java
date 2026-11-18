package com.careeros.inbound.service;

import com.careeros.ai.AiServiceClient;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.inbound.entity.InboundMail;
import com.careeros.inbound.repository.InboundMailRepository;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * The analyst's read of one letter (Epic 332).
 *
 * <p>Same discipline as every bridge in this service: it owns none of the judgment. The
 * letter travels to the ai-service exactly as it was stored — subject and body, nothing
 * else — and the answer comes back as the analyst's own {@code decode} (or {@code null}
 * when nothing in it stands). The reader's id scopes the letter read: another account's
 * letter id is the same 404 as a letter that never existed, and the decode never leaks
 * which one it was.
 *
 * <p>The endpoint is a read-then-call against the caller's own rows; the ai-service is
 * handed only that letter's words (the text is user data crossing a trust boundary, and
 * it travels as such — the relay never claims it is not data).
 */
@Service
public class InboundDecodeService {

    private final InboundMailRepository mails;
    private final AiServiceClient ai;

    public InboundDecodeService(InboundMailRepository mails, AiServiceClient ai) {
        this.mails = mails;
        this.ai = ai;
    }

    /**
     * {@code decode} is the analyst's own answer; absent when the analyst had nothing
     * grounded to say (relay down, letter too thin, an answer that invented a digit). The
     * rest of the response ({@code mailId}) is local scaffolding for the card.
     */
    @Transactional(readOnly = true)
    public Map<String, Object> decode(UUID userId, UUID mailId, String locale) {
        InboundMail mail = mails.findByIdAndUserId(mailId, userId)
                .orElseThrow(() -> new ApiException(ApiErrorCode.INBOUND_MAIL_NOT_FOUND,
                        "Reply not found"));

        Map<String, Object> letter = new LinkedHashMap<>();
        letter.put("subject", mail.getSubject());
        letter.put("body", mail.getBodyText());

        String language = normalizeLocale(locale);
        @SuppressWarnings("unchecked")
        Map<String, Object> answer =
                (Map<String, Object>) ai.decodeReply(userId, letter, language);

        Map<String, Object> out = new LinkedHashMap<>();
        out.put("mailId", mail.getId().toString());
        Object decode = answer == null ? null : answer.get("decode");
        if (decode != null) {
            out.put("decode", decode);
        }
        return out;
    }

    /** zh-prefixed means Chinese; anything else is English, matching the bridge's own rule. */
    private String normalizeLocale(String locale) {
        if (locale == null || locale.isBlank()) {
            return "en";
        }
        return locale.trim().toLowerCase(Locale.ROOT).startsWith("zh") ? "zh" : "en";
    }
}
