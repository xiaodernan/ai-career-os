package com.careeros.job.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.job.dto.SavedSearchDtos.Criteria;
import com.careeros.job.dto.SavedSearchDtos.SavedSearchItem;
import com.careeros.job.dto.SavedSearchDtos.SavedSearchRequest;
import com.careeros.job.entity.SavedSearch;
import com.careeros.job.repository.SavedSearchRepository;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

/**
 * What one saved search stores (roadmap 19.1).
 *
 * <p>The row is the question the nightly sweep will ask, so the test is about the
 * question rather than the CRUD: a criterion written with padding, a blank, a
 * repeated skill or `remote=false` has to land as the one canonical map the
 * matcher can compare against — otherwise two spellings of the same search
 * store differently and the alert path has to guess which one it is reading.
 */
class SavedSearchServiceTest {

    private final UUID userId = UUID.randomUUID();

    private SavedSearchRepository repository;
    private SavedSearchService service;

    @BeforeEach
    void setUp() {
        repository = mock(SavedSearchRepository.class);
        service = new SavedSearchService(repository);
        when(repository.save(any(SavedSearch.class))).thenAnswer(i -> i.getArgument(0));
    }

    @SuppressWarnings("unchecked")
    private SavedSearch saved() {
        ArgumentCaptor<SavedSearch> cap = ArgumentCaptor.forClass(SavedSearch.class);
        verify(repository).save(cap.capture());
        return cap.getValue();
    }

    @Test
    void storesTheCriteriaTrimmedAndWithoutTheFalseRemoteSwitch() {
        service.create(userId, new SavedSearchRequest("  Remote backend  ", new Criteria(
                " backend ", " Hangzhou ", "  ", false, 30000, 60000,
                List.of(" Java ", "java", "", "Spring"))));

        SavedSearch row = saved();
        assertThat(row.getUserId()).isEqualTo(userId);
        assertThat(row.getName()).isEqualTo("Remote backend");
        assertThat(row.getCriteria())
                .containsEntry("q", "backend")
                .containsEntry("location", "Hangzhou")
                .containsEntry("minSalary", 30000)
                .containsEntry("maxSalary", 60000)
                // Case is the board's own: its skill filter is an exact array match,
                // so "java" and "Java" are two filters and only an exact repeat folds.
                .containsEntry("skills", List.of("Java", "java", "Spring"))
                .doesNotContainKeys("company", "remote");
    }

    @Test
    void theStoredCriteriaReadBackAsTheWireShape() {
        SavedSearch row = new SavedSearch();
        row.setUserId(userId);
        row.setName("Remote");
        row.setCriteria(new java.util.LinkedHashMap<>(java.util.Map.of(
                "q", "backend", "remote", true, "skills", List.of("Java"), "minSalary", 30000)));
        when(repository.findByUserIdOrderByCreatedAtDesc(userId)).thenReturn(List.of(row));

        SavedSearchItem item = service.list(userId).get(0);

        assertThat(item.name()).isEqualTo("Remote");
        assertThat(item.criteria().q()).isEqualTo("backend");
        assertThat(item.criteria().remote()).isTrue();
        assertThat(item.criteria().minSalary()).isEqualTo(30000);
        assertThat(item.criteria().skills()).containsExactly("Java");
        assertThat(item.criteria().maxSalary()).isNull();
    }

    @Test
    void refusesASearchThatAsksNothing() {
        assertThatThrownBy(() -> service.create(userId,
                new SavedSearchRequest("Everything", new Criteria(null, null, null, false, null, null, null))))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.code()).isEqualTo(ApiErrorCode.SAVED_SEARCH_EMPTY));
    }

    @Test
    void refusesASalaryWindowThatCannotMatch() {
        assertThatThrownBy(() -> service.create(userId,
                new SavedSearchRequest("Inverted", new Criteria(null, null, null, null, 60000, 30000, null))))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.code()).isEqualTo(ApiErrorCode.SALARY_RANGE_INVALID));
    }

    @Test
    void deletingAnotherUsersSearchIsANotFound() {
        UUID id = UUID.randomUUID();
        when(repository.findByIdAndUserId(id, userId)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.delete(userId, id))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.code()).isEqualTo(ApiErrorCode.SAVED_SEARCH_NOT_FOUND));
    }
}
