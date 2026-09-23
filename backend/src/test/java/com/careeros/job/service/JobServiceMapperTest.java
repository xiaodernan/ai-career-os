package com.careeros.job.service;

import static org.assertj.core.api.Assertions.assertThat;

import com.careeros.job.dto.JobDtos.MatchSummary;
import com.careeros.job.entity.JobMatch;
import java.lang.reflect.Field;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;

/**
 * Binding-symmetry lock for {@link JobService#toSummary}: it forwards eleven {@link JobMatch}
 * getters into a positional record constructor. Five of them are adjacent {@code float} scores
 * (overall, technical, experience, projects, education) and three are adjacent {@code
 * List<Object>} fields (matchedSkills, missingSkills, evidence) — reordering any same-typed pair
 * compiles cleanly and would silently relabel every match score the UI shows. {@link JobMatch} is
 * written only by ai-service and exposes no setters, so the fixture is seeded by reflection.
 */
class JobServiceMapperTest {

    private static final UUID ID = UUID.fromString("11111111-1111-1111-1111-111111111111");
    private static final OffsetDateTime CREATED_AT =
            OffsetDateTime.of(2026, 3, 3, 11, 0, 0, 0, ZoneOffset.UTC);

    private static final List<Object> MATCHED = List.of("Java", "Spring Boot");
    private static final List<Object> MISSING = List.of("Kubernetes");
    private static final List<Object> EVIDENCE = List.of("exp-1", "proj-2");

    private static void setField(Object target, String name, Object value) {
        try {
            Field field = target.getClass().getDeclaredField(name);
            field.setAccessible(true);
            field.set(target, value);
        } catch (ReflectiveOperationException e) {
            throw new AssertionError("Unable to seed " + name + " on JobMatch", e);
        }
    }

    private static JobMatch fullyPopulated() {
        JobMatch m = new JobMatch();
        setField(m, "id", ID);
        setField(m, "overall", 0.86f);
        setField(m, "technical", 0.91f);
        setField(m, "experience", 0.72f);
        setField(m, "projects", 0.64f);
        setField(m, "education", 0.50f);
        setField(m, "matchedSkills", MATCHED);
        setField(m, "missingSkills", MISSING);
        setField(m, "evidence", EVIDENCE);
        setField(m, "narrative", "Strong backend fit");
        setField(m, "createdAt", CREATED_AT);
        return m;
    }

    @Test
    void everyMatchFieldLandsInItsOwnDtoSlot() {
        MatchSummary s = JobService.toSummary(fullyPopulated());

        assertThat(s.id()).isEqualTo(ID);
        assertThat(s.overall()).isEqualTo(0.86f);
        assertThat(s.technical()).isEqualTo(0.91f);
        assertThat(s.experience()).isEqualTo(0.72f);
        assertThat(s.projects()).isEqualTo(0.64f);
        assertThat(s.education()).isEqualTo(0.50f);
        assertThat(s.matchedSkills()).isEqualTo(MATCHED);
        assertThat(s.missingSkills()).isEqualTo(MISSING);
        assertThat(s.evidence()).isEqualTo(EVIDENCE);
        assertThat(s.narrative()).isEqualTo("Strong backend fit");
        assertThat(s.createdAt()).isEqualTo(CREATED_AT);
    }

    @Test
    void theFourSubScoreSlotsStayDistinct() {
        // technical / experience / projects / education are four consecutive floats: the exact
        // neighbourhood where a dropped or duplicated argument is invisible to the compiler.
        MatchSummary s = JobService.toSummary(fullyPopulated());

        assertThat(s.technical()).isEqualTo(0.91f);
        assertThat(s.experience()).isEqualTo(0.72f);
        assertThat(s.projects()).isEqualTo(0.64f);
        assertThat(s.education()).isEqualTo(0.50f);
        assertThat(List.of(s.technical(), s.experience(), s.projects(), s.education()))
                .doesNotHaveDuplicates();
    }

    @Test
    void theThreeListSlotsStayInOrder() {
        MatchSummary s = JobService.toSummary(fullyPopulated());

        assertThat(s.matchedSkills()).containsExactly("Java", "Spring Boot");
        assertThat(s.missingSkills()).containsExactly("Kubernetes");
        assertThat(s.evidence()).containsExactly("exp-1", "proj-2");
    }

    @Test
    void aBareMatchExposesZeroScoresAndEmptyCollections() {
        MatchSummary s = JobService.toSummary(new JobMatch());

        assertThat(s.id()).isNull();
        assertThat(s.narrative()).isNull();
        assertThat(s.createdAt()).isNull();
        // Primitive floats default to 0.0 and the entity initialises every list to List.of():
        // toItem must surface that faithfully rather than dropping the whole summary.
        assertThat(s.overall()).isZero();
        assertThat(s.technical()).isZero();
        assertThat(s.experience()).isZero();
        assertThat(s.projects()).isZero();
        assertThat(s.education()).isZero();
        assertThat(s.matchedSkills()).isEmpty();
        assertThat(s.missingSkills()).isEmpty();
        assertThat(s.evidence()).isEmpty();
    }
}
