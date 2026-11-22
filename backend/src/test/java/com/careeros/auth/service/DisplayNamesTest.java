package com.careeros.auth.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import org.junit.jupiter.api.Test;

/**
 * Epic 414 — the register fuzz accepted a bell, a newline, a zero-width space and
 * an RTL override as display names. None of those is a crash, but every one of
 * them can distort or spoof the name on a screen, so the door now stores the
 * cleaned read. These cases pin what survives and what is refused.
 */
class DisplayNamesTest {

    @Test
    void stripsControlsAndCollapsesWhitespaceToASingleLine() {
        assertThat(DisplayNames.clean("  Ada\u0007\n\t  Lovelace \u0000 ")).isEqualTo("Ada Lovelace");
    }

    @Test
    void foldsFullWidthAndMathematicalLettersWithNfkc() {
        assertThat(DisplayNames.clean("Ａｄａ  𝕳𝖆𝖈𝖐𝖊𝖗")).isEqualTo("Ada Hacker");
    }

    @Test
    void removesInvisibleDirectionalMarksAndKeepsEmojiSequences() {
        String cleaned = DisplayNames.clean("Ada\u202E 👩\u200D💻\u200B");
        assertThat(cleaned).isEqualTo("Ada 👩\u200D💻");
        assertThat(cleaned).doesNotContain("\u202E", "\u200B");
    }

    @Test
    void refusesANameWithNothingReadableLeft() {
        assertThatThrownBy(() -> DisplayNames.clean("\u0007\u200B\u202E  "))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.code()).isEqualTo(ApiErrorCode.VALIDATION_FAILED));
    }

    @Test
    void refusesANameThatExpandsPastTheLimitUnderNormalization() {
        // 70 code points in, 140 out: NFKC turns each ligature into two letters.
        assertThatThrownBy(() -> DisplayNames.clean("ﬁ".repeat(70)))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.code()).isEqualTo(ApiErrorCode.VALIDATION_FAILED));
    }

    @Test
    void leavesNullAlone() {
        assertThat(DisplayNames.clean(null)).isNull();
    }
}
