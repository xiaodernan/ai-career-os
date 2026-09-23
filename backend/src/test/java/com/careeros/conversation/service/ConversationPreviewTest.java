package com.careeros.conversation.service;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

/**
 * Pure-logic lock for {@link ConversationService#preview}: the conversation title is derived from
 * the first message and truncated at 60 characters. {@code String.length()} counts UTF-16 code
 * units, so a naive {@code substring(0, 60)} can cut a supplementary-character (emoji / astral CJK
 * extension) surrogate pair in half, yielding a lone surrogate — invalid in JSON and rendered as
 * mojibake in the UI. These tests pin the ordinary cases AND that truncation never splits a pair.
 */
class ConversationPreviewTest {

    /** True when {@code s} contains a surrogate not correctly paired with its neighbour. */
    private static boolean hasLoneSurrogate(String s) {
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (Character.isHighSurrogate(c)) {
                if (i + 1 >= s.length() || !Character.isLowSurrogate(s.charAt(i + 1))) {
                    return true;
                }
                i++; // consume the valid pair
            } else if (Character.isLowSurrogate(c)) {
                return true; // low surrogate with no preceding high surrogate
            }
        }
        return false;
    }

    @Test
    void blankOrNullFallsBackToTheSentinel() {
        assertThat(ConversationService.preview(null)).isEqualTo("New chat");
        assertThat(ConversationService.preview("")).isEqualTo("New chat");
        assertThat(ConversationService.preview("   \t\n ")).isEqualTo("New chat");
    }

    @Test
    void shortMessageIsTrimmedButNotEllipsised() {
        assertThat(ConversationService.preview("  hello there  ")).isEqualTo("hello there");
        // Exactly at the limit: returned whole, no ellipsis.
        String sixty = "a".repeat(60);
        assertThat(ConversationService.preview(sixty)).isEqualTo(sixty);
    }

    @Test
    void asciiOverLimitTruncatesToSixtyPlusEllipsis() {
        String out = ConversationService.preview("b".repeat(100));

        assertThat(out).hasSize(61).endsWith("…");
        assertThat(out.substring(0, 60)).isEqualTo("b".repeat(60));
        assertThat(hasLoneSurrogate(out)).isFalse();
    }

    @Test
    void bmpChineseSurvivesTheCutIntact() {
        // Most CJK lives in the BMP (one UTF-16 unit each) and is safe even split mid-string.
        String out = ConversationService.preview("求".repeat(80));

        assertThat(out).hasSize(61).endsWith("…");
        assertThat(hasLoneSurrogate(out)).isFalse();
    }

    @Test
    void truncationNeverSplitsASurrogatePair() {
        // 59 BMP chars fill units 0..58; the emoji occupies units 59 (high) and 60 (low). A naive
        // substring(0, 60) would keep the high surrogate and drop its low half -> lone surrogate.
        String message = "a".repeat(59) + "\uD83D\uDE00" + "tail";

        String out = ConversationService.preview(message);

        assertThat(hasLoneSurrogate(out))
                .as("preview must not emit an unpaired surrogate: %s", out)
                .isFalse();
        assertThat(out).endsWith("…");
        // The kept prefix must be a clean truncation of the original (whole code points only).
        assertThat(message.startsWith(out.substring(0, out.length() - 1))).isTrue();
    }
}
