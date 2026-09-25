package com.careeros.job.service;

import static org.assertj.core.api.Assertions.assertThat;

import com.careeros.job.dto.JobDtos.JobListItem;
import com.careeros.job.dto.JobDtos.MatchSummary;
import com.careeros.job.entity.Job;
import com.careeros.job.entity.JobMatch;
import java.lang.reflect.Field;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;

/**
 * Binding-symmetry lock for {@link JobService#toSummary}: it forwards thirteen {@link JobMatch}
 * getters into a positional record constructor. Five of them are adjacent {@code float} scores
 * (overall, technical, experience, projects, education) and five are adjacent {@code
 * List<Object>} fields (matchedSkills, missingSkills, evidence, whyMatch, preparation) — reordering
 * any same-typed pair compiles cleanly and would silently relabel every match score the UI shows.
 * {@link JobMatch} is written only by ai-service and exposes no setters, so the fixture is seeded by
 * reflection.
 */
class JobServiceMapperTest {

    private static final UUID ID = UUID.fromString("11111111-1111-1111-1111-111111111111");
    private static final OffsetDateTime CREATED_AT =
            OffsetDateTime.of(2026, 3, 3, 11, 0, 0, 0, ZoneOffset.UTC);

    private static final List<Object> MATCHED = List.of("Java", "Spring Boot");
    private static final List<Object> MISSING = List.of("Kubernetes");
    private static final List<Object> EVIDENCE = List.of("exp-1", "proj-2");
    private static final List<Object> WHY_MATCH =
            List.of("Your resume covers 2 of the 4 skills this JD lists: java, spring boot.");
    // Preparation items really are objects on the wire ({title,reason,priority}), so the fixture
    // holds a Map: a list of Strings would not catch a reader that flattened them to titles.
    private static final List<Object> PREPARATION =
            List.of(Map.of("title", "Add concrete evidence of kubernetes", "priority", "must"));

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
        setField(m, "whyMatch", WHY_MATCH);
        setField(m, "preparation", PREPARATION);
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
        assertThat(s.whyMatch()).isEqualTo(WHY_MATCH);
        assertThat(s.preparation()).isEqualTo(PREPARATION);
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
    void theFiveListSlotsStayInOrder() {
        MatchSummary s = JobService.toSummary(fullyPopulated());

        assertThat(s.matchedSkills()).containsExactly("Java", "Spring Boot");
        assertThat(s.missingSkills()).containsExactly("Kubernetes");
        assertThat(s.evidence()).containsExactly("exp-1", "proj-2");
        assertThat(s.whyMatch()).containsExactly(
                "Your resume covers 2 of the 4 skills this JD lists: java, spring boot.");
        assertThat(s.preparation()).containsExactly(
                Map.of("title", "Add concrete evidence of kubernetes", "priority", "must"));
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
        assertThat(s.whyMatch()).isEmpty();
        assertThat(s.preparation()).isEmpty();
    }

    // ---------------- toItem / JobListItem ----------------

    private static final UUID COMPANY_ID = UUID.fromString("22222222-2222-2222-2222-222222222222");
    private static final UUID JOB_ID = UUID.fromString("33333333-3333-3333-3333-333333333333");
    private static final OffsetDateTime POSTED_AT =
            OffsetDateTime.of(2026, 4, 4, 12, 0, 0, 0, ZoneOffset.UTC);

    private static Job populatedJob() {
        Job job = new Job();
        setField(job, "id", JOB_ID);
        job.setCompanyId(COMPANY_ID);
        job.setTitle("Senior Backend Engineer");
        job.setLocation("Shanghai");
        job.setRemoteType("hybrid");
        job.setEmploymentType("contract");
        job.setSalaryMin(30000);
        job.setSalaryMax(50000);
        job.setSalaryCurrency("CNY");
        job.setExperienceYears(5);
        job.setStatus("open");
        job.setSource("crawler");
        job.setExternalUrl("https://example.com/job/42");
        job.setSkills(List.of("Java", "Go"));
        setField(job, "postedAt", POSTED_AT);
        return job;
    }

    @Test
    void jobListItemMapsEveryFieldToItsOwnSlot() {
        JobListItem item = JobService.toItem(populatedJob(), "Acme Corp");

        assertThat(item.id()).isEqualTo(JOB_ID);
        assertThat(item.title()).isEqualTo("Senior Backend Engineer");
        assertThat(item.companyId()).isEqualTo(COMPANY_ID);
        assertThat(item.companyName()).isEqualTo("Acme Corp");
        assertThat(item.location()).isEqualTo("Shanghai");
        assertThat(item.remoteType()).isEqualTo("hybrid");
        assertThat(item.employmentType()).isEqualTo("contract");
        assertThat(item.salaryMin()).isEqualTo(30000);
        assertThat(item.salaryMax()).isEqualTo(50000);
        assertThat(item.salaryCurrency()).isEqualTo("CNY");
        assertThat(item.experienceYears()).isEqualTo(5);
        assertThat(item.status()).isEqualTo("open");
        assertThat(item.source()).isEqualTo("crawler");
        assertThat(item.externalUrl()).isEqualTo("https://example.com/job/42");
        assertThat(item.postedAt()).isEqualTo(POSTED_AT);
        assertThat(item.skills()).containsExactly("Java", "Go");
        // The list projection never carries match data; those slots stay null.
        assertThat(item.matchOverall()).isNull();
        assertThat(item.matchId()).isNull();
    }

    @Test
    void theSalaryRangeSlotsNeverCross() {
        // salaryMin / salaryMax are two adjacent Integers: swapping them compiles and renders an
        // inverted range the whole UI then trusts.
        JobListItem item = JobService.toItem(populatedJob(), "Acme Corp");

        assertThat(item.salaryMin()).isEqualTo(30000);
        assertThat(item.salaryMax()).isEqualTo(50000);
        assertThat(item.salaryMin()).isLessThan(item.salaryMax());
    }

    @Test
    void theAdjacentStringAndIntegerSlotsStayDistinct() {
        JobListItem item = JobService.toItem(populatedJob(), "Acme Corp");

        // companyName / location / remoteType / employmentType are four consecutive Strings, and
        // salaryMin / salaryMax / experienceYears are three consecutive Integers.
        assertThat(List.of(item.companyName(), item.location(), item.remoteType(),
                item.employmentType())).doesNotHaveDuplicates();
        assertThat(List.of(item.salaryMin(), item.salaryMax(), item.experienceYears()))
                .doesNotHaveDuplicates();
    }

    @Test
    void aBareJobFallsBackToEntityDefaultsAndNullOptionals() {
        JobListItem item = JobService.toItem(new Job(), "Acme Corp");

        assertThat(item.id()).isNull();
        assertThat(item.postedAt()).isNull();
        assertThat(item.companyId()).isNull();
        assertThat(item.location()).isNull();
        assertThat(item.externalUrl()).isNull();
        assertThat(item.matchOverall()).isNull();
        assertThat(item.matchId()).isNull();
        assertThat(item.skills()).isEmpty();
        // Entity-level defaults must pass through untouched.
        assertThat(item.companyName()).isEqualTo("Acme Corp");
        assertThat(item.remoteType()).isEqualTo("onsite");
        assertThat(item.employmentType()).isEqualTo("full_time");
        assertThat(item.salaryCurrency()).isEqualTo("CNY");
        assertThat(item.status()).isEqualTo("open");
        assertThat(item.source()).isEqualTo("user_paste");
    }
}
