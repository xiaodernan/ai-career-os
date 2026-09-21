package com.careeros.common;

import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;

/**
 * Native SQL queries return timestamp columns as OffsetDateTime or Instant depending on the
 * Hibernate/JDBC path; this normalizes both (and java.sql.Timestamp) to OffsetDateTime.
 */
public final class Times {

    private Times() {
    }

    public static OffsetDateTime offset(Object v) {
        if (v instanceof OffsetDateTime odt) {
            return odt;
        }
        if (v instanceof Instant instant) {
            return instant.atOffset(ZoneOffset.UTC);
        }
        if (v instanceof java.sql.Timestamp ts) {
            return ts.toInstant().atOffset(ZoneOffset.UTC);
        }
        return null;
    }
}
