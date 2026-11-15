package com.careeros.config;

import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.databind.DeserializationContext;
import com.fasterxml.jackson.databind.exc.MismatchedInputException;
import com.fasterxml.jackson.databind.deser.std.StringDeserializer;
import java.io.IOException;
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
}
