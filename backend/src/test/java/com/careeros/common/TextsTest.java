package com.careeros.common;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

/**
 * Locks the invariant behind {@link Texts}: truncating arbitrary user text by UTF-16 code units
 * must never leave a dangling half of a surrogate pair. These are the exact cases the excerpt
 * writers ({@code ResumeService.excerptOf}, {@code FileIngestService.excerptFor/titleFrom}) and
 * {@code ConversationService.preview} all rely on.
 */
class TextsTest {

    private static boolean hasLoneSurrogate(String s) {
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (Character.isHighSurrogate(c)) {
                if (i + 1 >= s.length() || !Character.isLowSurrogate(s.charAt(i + 1))) {
                    return true;
                }
                i++;
            } else if (Character.isLowSurrogate(c)) {
                return true;
            }
        }
        return false;
    }

    @Test
    void shortOrEmptyStringsAreReturnedWhole() {
        assertThat(Texts.truncate("", 10)).isEmpty();
        assertThat(Texts.truncate("abc", 10)).isEqualTo("abc");
        assertThat(Texts.truncate("abc", 3)).isEqualTo("abc");
        assertThat(Texts.safeCutIndex("abc", 3)).isEqualTo(3);
    }

    @Test
    void cutsOnUnitBoundaryWhenThePairIsNotStraddled() {
        String s = "a".repeat(10);
        assertThat(Texts.truncate(s, 5)).isEqualTo("aaaaa");
        assertThat(Texts.safeCutIndex(s, 5)).isEqualTo(5);
    }

    @Test
    void bmpCharactersNeedNoBackOff() {
        String s = "求".repeat(10); // each CJK ideograph is a single UTF-16 unit
        assertThat(Texts.truncate(s, 5)).isEqualTo("求".repeat(5));
        assertThat(hasLoneSurrogate(Texts.truncate(s, 5))).isFalse();
    }

    @Test
    void backsOffWhenTheCutWouldSplitAPair() {
        // units 0..4 are BMP; the emoji occupies units 5 (high) and 6 (low).
        String s = "a".repeat(5) + "\uD83D\uDE00" + "xyz";

        assertThat(Texts.safeCutIndex(s, 6)).isEqualTo(5);
        String out = Texts.truncate(s, 6);
        assertThat(out).isEqualTo("aaaaa");
        assertThat(hasLoneSurrogate(out)).isFalse();
    }

    @Test
    void keepsAWholePairWhenTheBoundaryFollowsIt() {
        // A full pair sits at units 3-4; cutting at 5 keeps the emoji intact (unit 4 is the LOW
        // half, so there is nothing to back off), and cutting at 6 would just add the next BMP char.
        String s = "abc" + "\uD83D\uDE00" + "xyz";

        assertThat(Texts.truncate(s, 5)).isEqualTo("abc\uD83D\uDE00");
        assertThat(Texts.truncate(s, 6)).isEqualTo("abc\uD83D\uDE00x");
        assertThat(hasLoneSurrogate(Texts.truncate(s, 6))).isFalse();
    }

    @Test
    void neverExceedsMaxUnitsAndNeverDropsMoreThanOneUnit() {
        String s = "a".repeat(9) + "\uD83D\uDE00" + "tail"; // pair straddles unit 10

        String out = Texts.truncate(s, 10);
        assertThat(out.length()).isBetween(9, 10);
        assertThat(hasLoneSurrogate(out)).isFalse();
        assertThat(s.startsWith(out)).isTrue();
    }
}
