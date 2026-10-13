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

    /** The kinds §17 names. An unknown one still shows what the extractor wrote, even when
     * the prompt no longer has a label for it. */
    public String label() {
        if (kind == null || kind.isBlank()) {
            return "Memory";
        }
        return switch (kind) {
            case "skill" -> "Skills";
            case "preference" -> "Preferences";
            case "profile" -> "Profile";
            case "interview" -> "Interview history";
            case "goal" -> "Goals";
            case "fact" -> "Facts";
            default -> kind;
        };
    }
}
