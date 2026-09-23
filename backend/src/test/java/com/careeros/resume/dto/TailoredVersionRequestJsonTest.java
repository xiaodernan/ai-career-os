package com.careeros.resume.dto;

import static org.assertj.core.api.Assertions.assertThat;

import com.careeros.resume.dto.ResumeDtos.TailoredVersionRequest;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.http.converter.json.Jackson2ObjectMapperBuilder;

/**
 * The body the tailoring panel posts has to land on the record's components. Spring Boot
 * deserialises request bodies with unknown properties ignored, so this mirrors that
 * configuration rather than Jackson's stricter default.
 */
class TailoredVersionRequestJsonTest {

    /**
     * Same builder Spring Boot's message converter uses, so "unknown properties are ignored"
     * is the real MVC behaviour rather than Jackson's stricter default.
     */
    private final ObjectMapper mapper = Jackson2ObjectMapperBuilder.json().build();

    private static final String BOTH_SPELLINGS = """
            {
              "resumeVersionId": "aaaaaaaa-0000-0000-0000-000000000001",
              "resume_version_id": "aaaaaaaa-0000-0000-0000-000000000001",
              "tailored": {"experience": [{"company": "ACME"}]},
              "diff": {"accepted": [], "rejected": []},
              "plaintext": "# Ada",
              "resumeId": "ignored-by-design"
            }
            """;

    @Test
    void theDualSpellingTheFrontendSendsBindsInsteadOfColliding() throws Exception {
        // The client sends the id under both names for tolerance; a constructor-binding
        // record that rejected the duplicate would 400 every save.
        TailoredVersionRequest bound = mapper.readValue(BOTH_SPELLINGS, TailoredVersionRequest.class);

        assertThat(bound.resumeVersionId().toString())
                .isEqualTo("aaaaaaaa-0000-0000-0000-000000000001");
        assertThat(bound.tailored()).containsKey("experience");
        assertThat(bound.diff()).containsKeys("accepted", "rejected");
        assertThat(bound.plaintext()).isEqualTo("# Ada");
    }

    @Test
    void snakeCaseOnlyBindsThroughTheAlias() throws Exception {
        TailoredVersionRequest bound = mapper.readValue(
                "{\"resume_version_id\":\"aaaaaaaa-0000-0000-0000-000000000002\","
                        + "\"tailored\":{\"profile\":{}},\"plaintext\":\"x\"}",
                TailoredVersionRequest.class);

        assertThat(bound.resumeVersionId().toString())
                .isEqualTo("aaaaaaaa-0000-0000-0000-000000000002");
        assertThat(bound.diff()).isNull();
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
}
