package com.careeros.ai.dto;

/**
 * One memory row as the browser reads it — the sentence the model stored, and the id it
 * would take to correct it.
 *
 * The JSON casing is the ai-service's own (camelCase there, unlike the backend's records),
 * so the controller maps it rather than declaring it. That is also why the two timestamps
 * are strings: they arrive pre-formatted and are never compared.
 */
public record MemoryItem(String id, String kind, String key, String content,
                         Double importance, String source, String createdAt,
                         String updatedAt) {
}
