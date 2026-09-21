package com.careeros.common;

import com.fasterxml.jackson.databind.ObjectMapper;

/** Shared mapper for writing envelopes from filters (outside the MVC converter stack). */
public final class EnvelopeJson {

    public static final ObjectMapper MAPPER = new ObjectMapper()
            .findAndRegisterModules()
            .disable(com.fasterxml.jackson.databind.SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);

    private EnvelopeJson() {
    }
}
