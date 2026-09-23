package com.careeros.common;

/**
 * Turns user text into a LIKE "contains" pattern with the wildcards neutralised.
 *
 * A search term is data, not a pattern: without this, "a_b" matches "axb", "%" matches
 * every row, and a term containing a backslash cannot find its own text (backslash is
 * LIKE's implicit escape character). Escaping with '!' instead of '\' keeps the result
 * independent of standard_conforming_strings — every call site must then emit
 * {@code ESCAPE '!'}.
 */
public final class LikePattern {

    private LikePattern() {
    }

    /** Pattern value for {@code col ILIKE :param ESCAPE '!'}. */
    public static String contains(String term) {
        if (term == null) {
            return null;
        }
        // '!' first: escaping it last would re-escape the escapes just introduced.
        String escaped = term.replace("!", "!!").replace("%", "!%").replace("_", "!_");
        return "%" + escaped + "%";
    }
}
