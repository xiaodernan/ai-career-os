package com.careeros.application.service;

import static org.assertj.core.api.Assertions.assertThat;

import com.careeros.application.dto.ApplicationDtos.ApplicationItem;
import com.careeros.application.entity.Application;
import java.lang.reflect.Field;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;

/**
 * Binding-symmetry lock for {@link ApplicationService#toItem}: it hands 15 entity values to a
 * positional record constructor, and several adjacent slots share a type (three UUIDs in a row,
 * title/companyName/status/notes as Strings, four OffsetDateTimes). Reordering two same-typed
 * arguments still compiles, so only a test that populates every field with a distinct value can
 * catch a silent cross-wire. {@code id}, {@code createdAt} and {@code updatedAt} have no setters
 * (the DB owns them), so they are injected by reflection to make those slots observable too.
 */
class ApplicationMapperTest {

    private static final UUID ID = UUID.fromString("00000000-0000-0000-0000-000000000001");
    private static final UUID JOB_ID = UUID.fromString("00000000-0000-0000-0000-000000000002");
    private static final UUID COMPANY_ID = UUID.fromString("00000000-0000-0000-0000-000000000003");
    private static final UUID RESUME_VERSION_ID = UUID.fromString("00000000-0000-0000-0000-00000000000a");
    private static final UUID JD_ID = UUID.fromString("00000000-0000-0000-0000-00000000000b");
    private static final UUID MATCH_ID = UUID.fromString("00000000-0000-0000-0000-00000000000c");

    private static final OffsetDateTime REMINDER_AT = at(2026, 6, 1, 9);
    private static final OffsetDateTime APPLIED_AT = at(2026, 4, 2, 10);
    private static final OffsetDateTime CREATED_AT = at(2026, 3, 3, 11);
    private static final OffsetDateTime UPDATED_AT = at(2026, 5, 4, 12);

    private static OffsetDateTime at(int y, int mo, int d, int h) {
        return OffsetDateTime.of(y, mo, d, h, 0, 0, 0, ZoneOffset.UTC);
    }

    private static void setField(Object target, String name, Object value) {
        try {
            Field field = target.getClass().getDeclaredField(name);
            field.setAccessible(true);
            field.set(target, value);
        } catch (ReflectiveOperationException e) {
            throw new AssertionError("Unable to seed " + name + " on Application", e);
        }
    }

    private static Application fullyPopulated() {
        Application app = new Application();
        setField(app, "id", ID);
        app.setUserId(UUID.fromString("00000000-0000-0000-0000-00000000000f"));
        app.setJobId(JOB_ID);
        app.setCompanyId(COMPANY_ID);
        app.setTitle("Senior Backend Engineer");
        app.setCompanyName("Acme Corp");
        app.setStatus("interview");
        app.setPosition(7);
        app.setNotes("met at career fair");
        app.setReminderAt(REMINDER_AT);
        app.setResumeVersionId(RESUME_VERSION_ID);
        app.setJdId(JD_ID);
        app.setMatchId(MATCH_ID);
        app.setAppliedAt(APPLIED_AT);
        setField(app, "createdAt", CREATED_AT);
        setField(app, "updatedAt", UPDATED_AT);
        return app;
    }

    @Test
    void everyEntityFieldLandsInItsOwnDtoSlot() {
        ApplicationItem item = ApplicationService.toItem(fullyPopulated());

        assertThat(item.id()).isEqualTo(ID);
        assertThat(item.jobId()).isEqualTo(JOB_ID);
        assertThat(item.companyId()).isEqualTo(COMPANY_ID);
        assertThat(item.title()).isEqualTo("Senior Backend Engineer");
        assertThat(item.companyName()).isEqualTo("Acme Corp");
        assertThat(item.status()).isEqualTo("interview");
        assertThat(item.position()).isEqualTo(7);
        assertThat(item.notes()).isEqualTo("met at career fair");
        assertThat(item.reminderAt()).isEqualTo(REMINDER_AT);
        assertThat(item.resumeVersionId()).isEqualTo(RESUME_VERSION_ID);
        assertThat(item.jdId()).isEqualTo(JD_ID);
        assertThat(item.matchId()).isEqualTo(MATCH_ID);
        assertThat(item.appliedAt()).isEqualTo(APPLIED_AT);
        assertThat(item.createdAt()).isEqualTo(CREATED_AT);
        assertThat(item.updatedAt()).isEqualTo(UPDATED_AT);
    }

    @Test
    void theThreeUuidForeignKeySlotsStayDistinct() {
        // resumeVersionId / jdId / matchId are consecutive UUIDs: the exact neighbourhood where a
        // dropped or duplicated argument is invisible to the compiler.
        ApplicationItem item = ApplicationService.toItem(fullyPopulated());

        assertThat(item.resumeVersionId()).isEqualTo(RESUME_VERSION_ID);
        assertThat(item.jdId()).isEqualTo(JD_ID);
        assertThat(item.matchId()).isEqualTo(MATCH_ID);
        assertThat(List.of(item.resumeVersionId(), item.jdId(), item.matchId()))
                .doesNotHaveDuplicates();
    }

    @Test
    void theFourDateSlotsStayDistinct() {
        // reminderAt / appliedAt / createdAt / updatedAt are all OffsetDateTime; createdAt and
        // updatedAt in particular are injected via reflection because the entity never exposes a
        // setter for them.
        ApplicationItem item = ApplicationService.toItem(fullyPopulated());

        assertThat(item.reminderAt()).isEqualTo(REMINDER_AT);
        assertThat(item.appliedAt()).isEqualTo(APPLIED_AT);
        assertThat(item.createdAt()).isEqualTo(CREATED_AT);
        assertThat(item.updatedAt()).isEqualTo(UPDATED_AT);
        assertThat(List.of(item.reminderAt(), item.appliedAt(), item.createdAt(), item.updatedAt()))
                .doesNotHaveDuplicates();
    }

    @Test
    void aBareApplicationExposesNullOptionalsAndNoPhantomIds() {
        ApplicationItem item = ApplicationService.toItem(new Application());

        assertThat(item.id()).isNull();
        assertThat(item.jobId()).isNull();
        assertThat(item.companyId()).isNull();
        assertThat(item.resumeVersionId()).isNull();
        assertThat(item.jdId()).isNull();
        assertThat(item.matchId()).isNull();
        assertThat(item.reminderAt()).isNull();
        assertThat(item.appliedAt()).isNull();
        assertThat(item.createdAt()).isNull();
        assertThat(item.updatedAt()).isNull();
        // Entity-level defaults that toItem must pass through unchanged.
        assertThat(item.status()).isEqualTo("saved");
        assertThat(item.position()).isZero();
    }
}
