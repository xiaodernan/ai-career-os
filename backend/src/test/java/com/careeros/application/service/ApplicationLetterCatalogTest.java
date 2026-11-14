package com.careeros.application.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.careeros.application.dto.ApplicationDtos.LetterCatalogItem;
import com.careeros.application.entity.Application;
import com.careeros.application.entity.ApplicationLetter;
import com.careeros.application.repository.ApplicationLetterRepository;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/**
 * The ink desk (Epic 210) — what the reader gets when they ask for every letter they kept.
 * The letter rows are caller-scoped all the way down, and the application titles ride along;
 * a letter whose application row was lost still answers, keyed to itself and to an empty title.
 * Nothing is synthesized, nothing is filtered silently.
 */
class ApplicationLetterCatalogTest {

    private static final UUID BOB = UUID.fromString("22222222-2222-4222-8222-222222222222");
    private static final UUID APP_A = UUID.fromString("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa");
    private static final UUID GHOST_APP = UUID.fromString("cccccccc-cccc-4ccc-8ccc-cccccccccccc");

    private final ApplicationLetterRepository letters = mock(ApplicationLetterRepository.class);
    private final ApplicationService applications = mock(ApplicationService.class);
    private final ApplicationLetterService service =
            new ApplicationLetterService(applications, letters);

    @BeforeEach
    void theShelfDefaultsToBobsOwn() {
        when(letters.findFirst200ByUserIdOrderByCreatedAtDescIdDesc(BOB)).thenReturn(List.of());
    }

    private static <T> T with(T target, String field, Object value) {
        try {
            var f = fieldOf(target.getClass(), field);
            f.setAccessible(true);
            f.set(target, value);
            return target;
        } catch (ReflectiveOperationException e) {
            throw new IllegalStateException(e);
        }
    }

    private static java.lang.reflect.Field fieldOf(Class<?> type, String name) throws NoSuchFieldException {
        Class<?> current = type;
        while (current != null) {
            try {
                return current.getDeclaredField(name);
            } catch (NoSuchFieldException e) {
                current = current.getSuperclass();
            }
        }
        throw new NoSuchFieldException(name);
    }

    private static ApplicationLetter letter(UUID applicationId, String body) {
        ApplicationLetter row = new ApplicationLetter();
        row.setApplicationId(applicationId);
        row.setUserId(BOB);
        row.setBody(body);
        with(row, "createdAt", OffsetDateTime.parse("2026-11-10T09:00:00Z"));
        return row;
    }

    private static Application app(UUID id, String title, String company) {
        Application row = new Application();
        row.setUserId(BOB);
        row.setTitle(title);
        row.setCompanyName(company);
        row.setStatus("applied");
        return with(row, "id", id);
    }

    @Test
    void theGalleryCarriesTheApplicationTitleAndCompanyNextToEveryLetter() {
        when(letters.findFirst200ByUserIdOrderByCreatedAtDescIdDesc(BOB))
                .thenReturn(List.of(letter(APP_A, "Dear Acme, I have read the incident reviews.")));
        when(applications.byIds(BOB, List.of(APP_A)))
                .thenReturn(List.of(app(APP_A, "Backend Engineer", "Acme")));

        List<LetterCatalogItem> out = service.catalog(BOB);

        assertThat(out).hasSize(1);
        assertThat(out.get(0).applicationTitle()).isEqualTo("Backend Engineer");
        assertThat(out.get(0).companyName()).isEqualTo("Acme");
        assertThat(out.get(0).body()).contains("incident reviews");
        assertThat(out.get(0).createdAt())
                .isEqualTo(OffsetDateTime.parse("2026-11-10T09:00:00Z"));
    }

    @Test
    void aLetterWhoseApplicationIsGoneStaysInTheGalleryWithAnEmptyTitle() {
        when(letters.findFirst200ByUserIdOrderByCreatedAtDescIdDesc(BOB))
                .thenReturn(List.of(letter(GHOST_APP, "Dear whoever reads this")));
        when(applications.byIds(BOB, List.of(GHOST_APP))).thenReturn(List.of());

        List<LetterCatalogItem> out = service.catalog(BOB);

        assertThat(out).hasSize(1);
        assertThat(out.get(0).applicationTitle()).isEmpty();
        assertThat(out.get(0).body()).contains("whoever reads this");
    }

    @Test
    void anEmptyShelfAnswersAnEmptyGalleryWithoutTouchingTheApplications() {
        assertThat(service.catalog(BOB)).isEmpty();
    }
}
