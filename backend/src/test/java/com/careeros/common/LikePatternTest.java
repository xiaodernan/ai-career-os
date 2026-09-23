package com.careeros.common;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

/**
 * Characterization for the LIKE escaper: '!' is the escape character, so it must be
 * doubled first (otherwise the escapes just inserted would be escaped again), and the
 * other two LIKE metacharacters must survive as literal text.
 */
class LikePatternTest {

    @Test
    void wildcardsBecomeEscapedLiteralsWrappedInContainsMatchers() {
        assertThat(LikePattern.contains("100% remote")).isEqualTo("%100!% remote%");
        assertThat(LikePattern.contains("a_b")).isEqualTo("%a!_b%");
    }

    @Test
    void escapeCharacterItselfIsDoubledAndFirst() {
        assertThat(LikePattern.contains("!")).isEqualTo("%!!%");
        // order matters: '!%' must encode as '!!' + '!%', not as an escaped '%'-escape
        assertThat(LikePattern.contains("!%")).isEqualTo("%!!!%%");
        assertThat(LikePattern.contains("%!")).isEqualTo("%!%!!%");
    }

    @Test
    void ordinaryAndEmptyTermsStillMatchAsSubstrings() {
        assertThat(LikePattern.contains("java")).isEqualTo("%java%");
        assertThat(LikePattern.contains("")).isEqualTo("%%");
        assertThat(LikePattern.contains(null)).isNull();
    }
}
