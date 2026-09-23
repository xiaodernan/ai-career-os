package com.careeros.common;

import java.util.Locale;

/**
 * Canonical salary contract: {@code jobs.salary_min/max} store an amount in the
 * currency's base unit per YEAR (for CNY that is 元/年, so 380000 renders as "38万").
 *
 * <p>This mirrors {@code V2__normalize_salary_units.sql} so the same rule can be
 * applied on the write path (which the migration cannot cover): scale unambiguously
 * legacy 万/年 values up and repair a min/max inversion. Kept lenient (repair, never
 * reject) so it cannot 400 a valid save or a client still sending legacy units.
 */
public final class SalaryRange {

    private SalaryRange() {
    }

    public record Range(Integer min, Integer max) {
    }

    public static Range normalize(Integer min, Integer max, String currency) {
        boolean perWan = isCny(currency);
        return swapIfNeeded(scale(min, perWan), scale(max, perWan));
    }

    /** A CNY annual salary strictly between 1 and 10_000 is a legacy 万/年 figure. */
    private static Integer scale(Integer value, boolean cny) {
        if (cny && value != null && value > 1 && value < 10_000) {
            return value * 10_000;
        }
        return value;
    }

    private static Range swapIfNeeded(Integer min, Integer max) {
        if (min != null && max != null && min > max) {
            return new Range(max, min);
        }
        return new Range(min, max);
    }

    private static boolean isCny(String currency) {
        if (currency == null) {
            return true; // the DB defaults salary_currency to 'CNY'
        }
        String c = currency.trim().toUpperCase(Locale.ROOT);
        return c.isEmpty() || c.equals("CNY") || c.equals("RMB");
    }
}
