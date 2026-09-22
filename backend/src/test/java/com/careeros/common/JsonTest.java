package com.careeros.common;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;

/** Pure coercion helpers that parse every ai-service response and jsonb column. */
class JsonTest {

    @Test
    void objAndArrGuardAgainstWrongTypes() {
        assertEquals(Map.of("a", 1), Json.obj(Map.of("a", 1)));
        assertTrue(Json.obj("nope").isEmpty());
        assertTrue(Json.obj(null).isEmpty());
        assertEquals(List.of(1, 2), Json.arr(List.of(1, 2)));
        assertTrue(Json.arr(Map.of()).isEmpty());
    }

    @Test
    void strListMapsNonNullsToStringsAndDropsNulls() {
        assertEquals(List.of("a", "2", "true"),
                Json.strList(java.util.Arrays.asList("a", 2, true, null)));
        assertTrue(Json.strList("not a list").isEmpty());
    }

    @Test
    void strStringifiesScalarsAndNullsOutMissing() {
        Map<String, Object> m = Map.of("s", "hi", "n", 7, "b", false);
        assertEquals("hi", Json.str(m, "s"));
        assertEquals("7", Json.str(m, "n"));
        assertEquals("false", Json.str(m, "b"));
        assertNull(Json.str(m, "absent"));
    }

    @Test
    void strOrFallsBackOnMissingOrBlank() {
        Map<String, Object> m = Map.of("present", "x", "blank", "   ");
        assertEquals("x", Json.strOr(m, "present", "fb"));
        assertEquals("fb", Json.strOr(m, "blank", "fb"));
        assertEquals("fb", Json.strOr(m, "absent", "fb"));
    }

    @Test
    void dblAcceptsNumbersAndNumericStrings() {
        Map<String, Object> m = Map.of("i", 3, "d", 2.5, "s", "1.75", "bad", "abc");
        assertEquals(3.0, Json.dbl(m, "i"));
        assertEquals(2.5, Json.dbl(m, "d"));
        assertEquals(1.75, Json.dbl(m, "s"));
        assertNull(Json.dbl(m, "bad"));
        assertNull(Json.dbl(m, "absent"));
    }

    @Test
    void fltUsesFallbackOnlyWhenUnparseable() {
        Map<String, Object> m = Map.of("d", 0.5);
        assertEquals(0.5f, Json.flt(m, "d", 0.9f));
        assertEquals(0.9f, Json.flt(m, "missing", 0.9f));
    }

    @Test
    void integerRoundsToNearestLongThenNarrows() {
        Map<String, Object> m = Map.of("up", 2.6, "down", 2.4, "s", "7", "bad", "x");
        assertEquals(3, Json.integer(m, "up"));
        assertEquals(2, Json.integer(m, "down"));
        assertEquals(7, Json.integer(m, "s"));
        assertNull(Json.integer(m, "bad"));
    }

    @Test
    void uuidOrNullParsesValidAndRejectsJunk() {
        UUID id = UUID.randomUUID();
        Map<String, Object> m = Map.of("good", id.toString(), "blank", "  ", "junk", "not-a-uuid");
        assertEquals(id, Json.uuidOrNull(m, "good"));
        assertNull(Json.uuidOrNull(m, "blank"));
        assertNull(Json.uuidOrNull(m, "absent"));
        assertNull(Json.uuidOrNull(m, "junk"));
    }
}
