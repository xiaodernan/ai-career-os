package com.careeros.config;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.json.JsonMapper;
import com.fasterxml.jackson.databind.module.SimpleModule;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import org.junit.jupiter.api.Test;

/**
 * The decode door the shelf deadline goes through (Epic 337): one narrow deserializer,
 * every shape the wire can carry that the handler used to bounce — and the shapes it must
 * still bounce so a fuzzer learns nothing.
 */
class JacksonConfigTest {

    private ObjectMapper mapper() {
        ObjectMapper mapper = JsonMapper.builder()
                .configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false)
                .addModule(new com.fasterxml.jackson.datatype.jsr310.JavaTimeModule())
                .addModule(new SimpleModule()
                        .addDeserializer(OffsetDateTime.class, new JacksonConfig.LenientOffsetDateTimeDeserializer()))
                .build();
        return mapper;
    }

    record Fake(OffsetDateTime deadline) {}

    @Test
    void a_bare_date_is_the_utc_start_of_day() throws Exception {
        Fake fake = mapper().readValue("{\"deadline\":\"2026-12-15\"}", Fake.class);
        assertThat(fake.deadline()).isEqualTo(
                OffsetDateTime.of(2026, 12, 15, 0, 0, 0, 0, ZoneOffset.UTC));
    }

    @Test
    void an_offset_datetime_keeps_its_offset() throws Exception {
        Fake fake = mapper().readValue("{\"deadline\":\"2026-12-15T10:30:00+08:00\"}", Fake.class);
        assertThat(fake.deadline().getOffset()).isEqualTo(ZoneOffset.ofHours(8));
        assertThat(fake.deadline().getHour()).isEqualTo(10);
    }

    @Test
    void a_zoned_datetime_keeps_its_instant() throws Exception {
        Fake fake = mapper().readValue("{\"deadline\":\"2026-12-15T00:00:00Z\"}", Fake.class);
        assertThat(fake.deadline().getOffset()).isEqualTo(ZoneOffset.UTC);
        assertThat(fake.deadline().toLocalDate().toString()).isEqualTo("2026-12-15");
    }

    @Test
    void garbage_still_fails_at_the_decode_layer() {
        assertThatThrownBy(() -> mapper().readValue("{\"deadline\":\"next tuesday\"}", Fake.class))
                .isInstanceOf(com.fasterxml.jackson.databind.exc.MismatchedInputException.class);
    }

    @Test
    void a_null_string_is_not_a_silent_passthrough() throws Exception {
        Fake fake = mapper().readValue("{\"deadline\":null}", Fake.class);
        assertThat(fake.deadline()).isNull();
    }
}
