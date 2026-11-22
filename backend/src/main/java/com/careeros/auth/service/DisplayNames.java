package com.careeros.auth.service;

import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import java.text.Normalizer;
import java.util.regex.Pattern;

/**
 * Epic 414 — a display name is drawn on every screen the reader owns, so what the
 * register door stores has to be a name a screen can draw. The adversarial fuzz
 * (2026-11-22) found the door accepting a bell character, a line break, a
 * zero-width space and an RTL override with a 201: none of them is a 5xx, but
 * each is a way to distort or spoof the name in a header, a nav or an export.
 *
 * <p>Cleaning is deterministic and lossless for real names: NFKC folds the
 * full-width and mathematical letters a reader might paste, control characters
 * and the invisible directional/zero-width marks are removed, and runs of spaces
 * collapse to one. Emoji survive — including ZWJ sequences — because those are
 * symbols, not controls. A value with nothing readable left is refused with the
 * same VALIDATION_FAILED every other blank field uses rather than stored as an
 * empty name.
 */
final class DisplayNames {

    /** C0/C1 controls, zero-width space, bidi marks and isolates. ZWJ is kept for emoji. */
    private static final Pattern INVISIBLE_OR_CONTROL = Pattern.compile(
            "[\\p{Cc}\\u200B\\u200E\\u200F\\u202A-\\u202E\\u2066-\\u2069\\u061C]");

    /** Any Unicode whitespace run, including the no-break and narrow no-break spaces. */
    private static final Pattern SPACE_RUN = Pattern.compile("[\\s\\u00A0\\u2007\\u202F]+");

    private static final int MAX_CODE_POINTS = 120;

    private DisplayNames() {
    }

    static String clean(String raw) {
        if (raw == null) {
            return null;
        }
        String stripped = INVISIBLE_OR_CONTROL.matcher(
                Normalizer.normalize(raw, Normalizer.Form.NFKC)).replaceAll("");
        String squeezed = SPACE_RUN.matcher(stripped).replaceAll(" ").strip();
        if (squeezed.isEmpty()) {
            throw new ApiException(ApiErrorCode.VALIDATION_FAILED, "Display name has no readable characters");
        }
        if (squeezed.codePointCount(0, squeezed.length()) > MAX_CODE_POINTS) {
            throw new ApiException(ApiErrorCode.VALIDATION_FAILED, "Display name is too long");
        }
        return squeezed;
    }
}
