package com.careeros.common;

/** Text utilities for safely handling user-supplied strings. */
public final class Texts {

    private Texts() {
    }

    /**
     * Highest exclusive index &le; {@code maxUnits} at which {@code s} may be cut without
     * splitting a UTF-16 surrogate pair. {@link String#length()} and {@link String#substring}
     * count code <em>units</em>, so a naive {@code substring(0, maxUnits)} can leave a lone high
     * surrogate when a supplementary character (emoji, astral CJK extension) straddles the
     * boundary — invalid in JSON and rejected by PostgreSQL's UTF-8 {@code text} columns.
     */
    public static int safeCutIndex(String s, int maxUnits) {
        if (s.length() <= maxUnits) {
            return s.length();
        }
        // Unit at maxUnits-1 is the last one we would keep; if it opens a pair, drop it.
        return Character.isHighSurrogate(s.charAt(maxUnits - 1)) ? maxUnits - 1 : maxUnits;
    }

    /** Truncate {@code s} to at most {@code maxUnits} code units, never splitting a surrogate pair. */
    public static String truncate(String s, int maxUnits) {
        return s.substring(0, safeCutIndex(s, maxUnits));
    }
}
