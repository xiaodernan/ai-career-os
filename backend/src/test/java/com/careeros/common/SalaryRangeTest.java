package com.careeros.common;

import static com.careeros.common.SalaryRange.normalize;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

import org.junit.jupiter.api.Test;

/** Write-path mirror of {@code V2__normalize_salary_units.sql}; the migration cannot fix new rows. */
class SalaryRangeTest {

    @Test
    void scalesUnambiguousLegacyWanCnyValues() {
        assertEquals(new SalaryRange.Range(380_000, 450_000), normalize(38, 45, "CNY"));
        assertEquals(new SalaryRange.Range(300_000, 450_000), normalize(30, 45, "RMB"));
        // case / whitespace insensitive
        assertEquals(new SalaryRange.Range(300_000, null), normalize(30, null, " cny "));
    }

    @Test
    void respectsExclusiveBoundsAndLeavesNullAndZeroAlone() {
        assertEquals(10_000, normalize(10_000, null, "CNY").min()); // 10_000 is a plausible 元 figure
        assertEquals(1, normalize(1, null, "CNY").min());           // <= 1 untouched
        assertEquals(0, normalize(0, null, "CNY").min());
        assertEquals(10_001, normalize(10_001, null, "CNY").min());
        assertNull(normalize(null, null, "CNY").min());
        assertNull(normalize(null, null, "CNY").max());
    }

    @Test
    void neverScalesNonCnyOrAlreadyCorrectRows() {
        assertEquals(new SalaryRange.Range(30, 45), normalize(30, 45, "USD"));
        assertEquals(new SalaryRange.Range(380_000, 450_000), normalize(380_000, 450_000, "CNY"));
    }

    @Test
    void nullCurrencyTreatedAsCnyMatchesDbDefault() {
        assertEquals(new SalaryRange.Range(300_000, null), normalize(30, null, null));
    }

    @Test
    void repairsInversionAfterScaling() {
        assertEquals(new SalaryRange.Range(300_000, 450_000), normalize(450_000, 300_000, "USD"));
        assertEquals(new SalaryRange.Range(300_000, 450_000), normalize(45, 30, "CNY")); // scale then swap
        // one-sided range must not be "inverted" into a swap
        assertEquals(new SalaryRange.Range(300_000, null), normalize(30, null, "CNY"));
    }
}
