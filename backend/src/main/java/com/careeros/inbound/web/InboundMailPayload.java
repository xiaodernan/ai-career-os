package com.careeros.inbound.web;

import com.fasterxml.jackson.databind.JsonNode;

/**
 * The five facts the inbound webhook reads from Postmark's delivery (roadmap 37.1).
 *
 * <p>The vendor's spellings stop at {@link #fromPostmark}: the controller binds the provider's
 * JSON and hands this record on, so no other class in the backend knows what Postmark calls a
 * subject. Other providers send the same facts under other names; a deployment pointing one at
 * this route maps them in the provider's own transform, because a second parser here would be a
 * second contract to keep true. Anything else in the payload -- the HTML body, the attachments --
 * is ignored: the reader reads text, and an attachment is not something this product can open
 * safely.
 */
public record InboundMailPayload(String messageId, String from, String subject, String textBody, String date) {

    static InboundMailPayload fromPostmark(JsonNode body) {
        return new InboundMailPayload(
                text(body, "MessageID"),
                text(body, "From"),
                text(body, "Subject"),
                text(body, "TextBody"),
                text(body, "Date"));
    }

    /** One key's text: a missing key or a body that is not an object reads as absent, not an error. */
    private static String text(JsonNode body, String key) {
        JsonNode value = body == null ? null : body.get(key);
        return value == null || value.isNull() ? null : value.asText();
    }
}
