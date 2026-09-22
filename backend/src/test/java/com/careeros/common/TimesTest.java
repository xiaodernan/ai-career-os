package com.careeros.common;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertSame;

import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import org.junit.jupiter.api.Test;

/** Normalizes the varying native-SQL timestamp types into a single OffsetDateTime shape. */
class TimesTest {

    private static final Instant INSTANT = Instant.parse("2026-09-22T10:15:30Z");

    @Test
    void offsetDateTimePassesThroughUnchanged() {
        OffsetDateTime odt = INSTANT.atOffset(ZoneOffset.UTC);
        assertSame(odt, Times.offset(odt));
    }

    @Test
    void offsetDateTimeKeepsItsOwnOffset() {
        ZoneOffset plus530 = ZoneOffset.ofHoursMinutes(5, 30);
        OffsetDateTime odt = INSTANT.atOffset(plus530);
        OffsetDateTime out = Times.offset(odt);
        assertEquals(plus530, out.getOffset());
        assertEquals(odt.toLocalDateTime(), out.toLocalDateTime());
    }

    @Test
    void instantAnchorsToUtc() {
        assertEquals(INSTANT.atOffset(ZoneOffset.UTC), Times.offset(INSTANT));
    }

    @Test
    void sqlTimestampAnchorsToUtc() {
        assertEquals(INSTANT.atOffset(ZoneOffset.UTC), Times.offset(java.sql.Timestamp.from(INSTANT)));
    }

    @Test
    void unsupportedAndNullYieldNull() {
        assertNull(Times.offset(null));
        assertNull(Times.offset("2026-09-22T10:15:30Z"));
        assertNull(Times.offset(INSTANT.toEpochMilli()));
    }
}
