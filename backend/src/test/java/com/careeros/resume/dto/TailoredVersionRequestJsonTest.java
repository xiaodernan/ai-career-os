package com.careeros.resume.dto;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatExceptionOfType;

import com.careeros.resume.dto.ResumeDtos.TailoredVersionRequest;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.http.converter.json.Jackson2ObjectMapperBuilder;

/**
 * The body the tailoring panel posts has to land on the record's components. Spring Boot
 * deserialises request bodies with unknown properties ignored, so this mirrors that
 * configuration rather than Jackson's stricter default.
 *
 * <p>The one thing a caller may not do is send the same field under both its name and its alias.
 * {@code @JsonAlias} makes both spellings resolve to a single constructor property, and a record
 * has no setter for a second value to fall back on, so Jackson aborts the whole request. This was
 * not theoretical: every dual-spelling body the frontend used to build died that way, and the
 * {@link #bothSpellingsOfOneFieldCannotBeBound} case is kept here because the failure is
 * non-obvious — it depends on how many other fields the body carries, so a payload that happens
 * to work invites the next one.
 */
class TailoredVersionRequestJsonTest {

    /**
     * Same builder Spring Boot's message converter uses, so "unknown properties are ignored"
     * is the real MVC behaviour rather than Jackson's stricter default.
     */
    private final ObjectMapper mapper = Jackson2ObjectMapperBuilder.json().build();

    private static final String CAMEL = """
            {
              "tailored": {"experience": [{"company": "ACME"}]},
              "diff": {"accepted": [], "rejected": []},
              "plaintext": "# Ada",
              "resumeVersionId": "aaaaaaaa-0000-0000-0000-000000000001"
            }
            """;

    private static final String SNAKE = """
            {
              "tailored": {"experience": [{"company": "ACME"}]},
              "diff": {"accepted": [], "rejected": []},
              "plaintext": "# Ada",
              "resume_version_id": "aaaaaaaa-0000-0000-0000-000000000001"
            }
            """;

    private static final String BOTH = """
            {
              "tailored": {"experience": [{"company": "ACME"}]},
              "diff": {"accepted": [], "rejected": []},
              "plaintext": "# Ada",
              "resumeVersionId": "aaaaaaaa-0000-0000-0000-000000000001",
              "resume_version_id": "aaaaaaaa-0000-0000-0000-000000000001"
            }
            """;

    @Test
    void camelCaseIsTheRecordsOwnNameAndBinds() throws Exception {
        TailoredVersionRequest bound = mapper.readValue(CAMEL, TailoredVersionRequest.class);

        assertThat(bound.resumeVersionId().toString())
                .isEqualTo("aaaaaaaa-0000-0000-0000-000000000001");
        assertThat(bound.tailored()).containsKey("experience");
        assertThat(bound.diff()).containsKeys("accepted", "rejected");
        assertThat(bound.plaintext()).isEqualTo("# Ada");
    }

    @Test
    void snakeCaseBindsThroughTheAliasToTheSameComponent() throws Exception {
        TailoredVersionRequest bound = mapper.readValue(SNAKE, TailoredVersionRequest.class);

        assertThat(bound.resumeVersionId().toString())
                .isEqualTo("aaaaaaaa-0000-0000-0000-000000000001");
    }

    @Test
    void bothSpellingsOfOneFieldCannotBeBound() {
        // Identical values, still fatal: the alias resolves to the same constructor property and
        // there is no setter to absorb the repeat. GlobalExceptionHandler answers this 400.
        assertThatExceptionOfType(com.fasterxml.jackson.databind.exc.InvalidDefinitionException.class)
                .isThrownBy(() -> mapper.readValue(BOTH, TailoredVersionRequest.class))
                .withMessageContaining("No fallback setter/field defined for creator property");
    }

    @Test
    void anOmittedBaseVersionIsNotNullButAbsentSoTheServerPicksTheCurrentResume() throws Exception {
        TailoredVersionRequest bound = mapper.readValue(
                "{\"tailored\":{}}", TailoredVersionRequest.class);

        assertThat(bound.resumeVersionId()).isNull();
        assertThat(bound.plaintext()).isNull();
    }

    @Test
    void anExplicitNullTailoredReachesTheServiceGuardNotAParseError() throws Exception {
        // saveTailoredDraft is what answers 400 for a missing structured body — if binding
        // failed first, the client would see a parse error instead of that message.
        TailoredVersionRequest bound =
                mapper.readValue("{\"tailored\":null}", TailoredVersionRequest.class);
        assertThat(bound.tailored()).isNull();
    }

    @Test
    void anUnknownFieldIsIgnoredRatherThanRejected() throws Exception {
        TailoredVersionRequest bound = mapper.readValue(
                "{\"tailored\":{},\"resumeId\":\"ignored-by-design\"}", TailoredVersionRequest.class);

        assertThat(bound.tailored()).isEmpty();
    }
}
