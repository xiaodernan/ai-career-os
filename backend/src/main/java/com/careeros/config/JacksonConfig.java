package com.careeros.config;

import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.databind.DeserializationContext;
import com.fasterxml.jackson.databind.exc.MismatchedInputException;
import com.fasterxml.jackson.databind.deser.std.StringDeserializer;
import com.fasterxml.jackson.databind.deser.std.StdDeserializer;
import java.io.IOException;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeParseException;
import org.springframework.boot.autoconfigure.jackson.Jackson2ObjectMapperBuilderCustomizer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * The NUL-byte door (Epic 234).
 *
 * <p>PostgreSQL forbids the U+0000 character in text columns, so a request body carrying one
 * reached the database and exploded at flush time as an unconstrained 500 — and Epic 226's
 * deferred-flush bug showed the same failure surfacing at commit, beyond any try/catch in
 * the service. Rejecting the byte at the decode layer turns the whole class into a clean
 * 400: Jackson cannot bind the body, {@code HttpMessageNotReadableException} maps to
 * MALFORMED_REQUEST, and no caller learns anything by fuzzing.
 *
 * <p>This is a custom {@code String} deserializer rather than a filter: bodies arrive as
 * megabytes (voice upload, ingestion feeds), and scanning raw bytes would punish every
 * legitimate request to catch a pathological one. The deserializer sees exactly the strings
 * the application binds, and only those.
 *
 * <p>The same decode door also carries the deadline shim (Epic 337): a custom
 * {@code OffsetDateTime} deserializer that accepts the instant the API already speaks and
 * the bare {@code yyyy-MM-dd} the shelf's date input sends as UTC-start-of-day — one bean,
 * two narrow doors, everything else fails at the same place it always did.
 */
@Configuration
public class JacksonConfig {

    /** One NUL check per bound string — everything else delegates to the stock behavior. */
    static final class NoNulStringDeserializer extends StringDeserializer {
        @Override
        public String deserialize(JsonParser parser, DeserializationContext ctxt) throws IOException {
            String value = super.deserialize(parser, ctxt);
            if (value != null && value.indexOf('\u0000') >= 0) {
                throw MismatchedInputException.from(parser, String.class,
                        "the U+0000 byte is not legal in a request field");
            }
            return value;
        }
    }

    @Bean
    public Jackson2ObjectMapperBuilderCustomizer noNulStringDeserializer() {
        return builder -> builder.deserializerByType(String.class, new NoNulStringDeserializer());
    }

    /**
     * The date the browser sends (UTC-start). The shelf's date input posts bare
     * {@code yyyy-MM-dd}, and the stock OffsetDateTime binding refuses it outright — every shelf
     * write with a deadline was a 400 the client could see as nothing but a failure toast.
     * Accept the two shapes the UI can send: the instant the rest of the API speaks, and the
     * bare date as UTC-start-of-day. Anything else still fails at the decode layer.
     */
    static final class LenientOffsetDateTimeDeserializer extends StdDeserializer<OffsetDateTime> {
        LenientOffsetDateTimeDeserializer() {
            super(OffsetDateTime.class);
        }

        @Override
        public OffsetDateTime deserialize(JsonParser parser, DeserializationContext ctxt) throws IOException {
            String s = parser.getValueAsString().trim();
            try {
                return OffsetDateTime.parse(s);
            } catch (DateTimeParseException first) {
                try {
                    return LocalDate.parse(s).atStartOfDay().atOffset(ZoneOffset.UTC);
                } catch (DateTimeParseException second) {
                    throw MismatchedInputException.from(parser, OffsetDateTime.class,
                            "the deadline is not an ISO-8601 date or datetime");
                }
            }
        }
    }

    @Bean
    public Jackson2ObjectMapperBuilderCustomizer lenientOffsetDateTimeDeserializer() {
        return builder -> builder.deserializerByType(OffsetDateTime.class, new LenientOffsetDateTimeDeserializer());
    }
}
