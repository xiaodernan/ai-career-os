package com.careeros.config;

import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.careeros.config.JacksonConfig.NoNulStringDeserializer;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.module.SimpleModule;
import java.util.Map;
import org.junit.jupiter.api.Test;

/**
 * Epic 234 — the NUL door, pinned at the seam every bound string passes through.
 *
 * PostgreSQL forbids U+0000 in text columns, and Epic 233's fuzz run showed the byte
 * reaching the database and exploding as an unconstrained 500. The deserializer must
 * refuse the byte before the service ever sees it, so the global handler answers
 * MALFORMED_REQUEST instead of the caller learning about our insides.
 */
class JacksonConfigTest {

    private final ObjectMapper mapper = new ObjectMapper()
            .registerModule(new SimpleModule().addDeserializer(String.class, new NoNulStringDeserializer()));

    @Test
    void aStringCarryingTheNulByteIsRefusedAtTheDeserializer() {
        assertThatThrownBy(() -> mapper.readValue("{\"name\":\"no\\u0000l\"}", Map.class))
                .hasMessageContaining("U+0000");
    }

    @Test
    void ordinaryStringsPassThroughUntouched() throws Exception {
        @SuppressWarnings("unchecked")
        Map<String, Object> parsed = mapper.readValue("{\"name\":\"plain \"}", Map.class);
        org.assertj.core.api.Assertions.assertThat(parsed.get("name")).isEqualTo("plain ");
    }
}
