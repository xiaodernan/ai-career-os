package com.careeros.job.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.ai.AiServiceClient;
import com.careeros.application.service.ApplicationService;
import com.careeros.common.Paging;
import com.careeros.job.dto.JobDtos.CompanyDetail;
import com.careeros.job.dto.JobDtos.JobListItem;
import com.careeros.job.entity.Company;
import com.careeros.job.repository.CompanyRepository;
import com.careeros.job.repository.JobJdRepository;
import com.careeros.job.repository.JobMatchRepository;
import com.careeros.job.repository.JobRepository;
import com.careeros.job.repository.JobSearchRepository;
import com.careeros.job.repository.SavedJobRepository;
import com.careeros.resume.service.ResumeService;
import com.careeros.search.service.QueryEmbeddingService;
import com.careeros.support.TestTransactions;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.test.util.ReflectionTestUtils;

/**
 * The company page's two halves come from one filter set.
 *
 * <p>The heading's number and the rows under it have to be answers to the same question — this repo
 * has already paid for that lesson once, on the dashboard's attention card, where a count kept
 * working while the list behind it 500'd. Here the risk is the other direction: a profile that counts
 * its roles with {@code countOpenRoles} and lists them with a different predicate shows "4 open roles"
 * over three rows.
 *
 * <p>Plain Mockito: the search statement itself is guarded by {@code JobSearchRepositoryTest} and the
 * integration suite, so what is checked here is that one {@code Filters} value reaches both calls.
 */
class JobServiceCompanyDetailTest {

    private final UUID userId = UUID.randomUUID();
    private final UUID companyId = UUID.randomUUID();

    private CompanyRepository companies;
    private JobSearchRepository search;
    private JobService service;

    @BeforeEach
    void setUp() {
        companies = mock(CompanyRepository.class);
        search = mock(JobSearchRepository.class);
        service = new JobService(mock(JobRepository.class), companies, mock(JobJdRepository.class),
                mock(SavedJobRepository.class), mock(JobMatchRepository.class), search,
                mock(ResumeService.class), mock(ApplicationService.class),
                mock(AiServiceClient.class), mock(QueryEmbeddingService.class),
                TestTransactions.executing());
    }

    private Company researched() {
        Company c = new Company();
        ReflectionTestUtils.setField(c, "id", companyId);
        c.setName("星海智能 StarSea AI");
        c.setIndustry("人工智能");
        c.setCulture("研究驱动，工程师文化。");
        c.setInterviewProcess("简历筛选 → 技术一面 → 技术二面 → HR 面");
        c.setSources(List.<Object>of(Map.of("type", "synthetic_demo", "note", "Demo seed data.")));
        when(companies.findById(companyId)).thenReturn(Optional.of(c));
        return c;
    }

    private JobSearchRepository.Filters captured() {
        ArgumentCaptor<JobSearchRepository.Filters> cap =
                ArgumentCaptor.forClass(JobSearchRepository.Filters.class);
        verify(search).search(cap.capture());
        return cap.getValue();
    }

    @Test
    void theRowsAndTheHeadingAreOnePredicate() {
        researched();
        when(search.search(any())).thenReturn(List.of());
        when(search.count(any())).thenReturn(4L);

        CompanyDetail detail = service.companyDetail(userId, companyId);

        JobSearchRepository.Filters f = captured();
        assertThat(f.companyId()).isEqualTo(companyId);
        assertThat(f.status()).isEqualTo("open");
        assertThat(f.sort()).as("best match first: the point of a company page is the roles worth opening")
                .isEqualTo("match");
        assertThat(f.userId()).isEqualTo(userId);
        assertThat(f.page()).isZero();
        assertThat(f.size()).isEqualTo(Paging.MAX_PAGE_SIZE);

        // The count is asked with the same filter value the list was, which is the whole claim.
        ArgumentCaptor<JobSearchRepository.Filters> counted =
                ArgumentCaptor.forClass(JobSearchRepository.Filters.class);
        verify(search).count(counted.capture());
        assertThat(counted.getValue()).isEqualTo(f);

        assertThat(detail.company().openRoleCount()).isEqualTo(4L);
        // ...and not the other count query, which would be a second definition of "open".
        verify(companies, never()).countOpenRoles(any());
    }

    @Test
    void theProfileCarriesWhatTheWritePathHasAlwaysAccepted() {
        // `culture`, `interviewProcess` and `sources` are stored on the row and were dropped by every
        // read path, so a researched profile could be posted and never seen again.
        researched();
        when(search.search(any())).thenReturn(List.of());
        when(search.count(any())).thenReturn(0L);

        var item = service.companyDetail(userId, companyId).company();

        assertThat(item.name()).isEqualTo("星海智能 StarSea AI");
        assertThat(item.culture()).isEqualTo("研究驱动，工程师文化。");
        assertThat(item.interviewProcess()).isEqualTo("简历筛选 → 技术一面 → 技术二面 → HR 面");
        assertThat(item.sources()).containsExactly(Map.of("type", "synthetic_demo",
                "note", "Demo seed data."));
    }

    @Test
    void theRolesAreTheBoardsOwnRows() {
        researched();
        JobListItem row = new JobListItem(UUID.randomUUID(), "Agent 平台工程师", companyId,
                "星海智能 StarSea AI", "上海", "hybrid", "full_time", 400000, 700000, "CNY", 5,
                "open", "seed", null, null, List.of("Python"), 0.86f, UUID.randomUUID());
        when(search.search(any())).thenReturn(List.of(row));
        when(search.count(any())).thenReturn(1L);

        assertThat(service.companyDetail(userId, companyId).openRoles()).containsExactly(row);
    }

    @Test
    void anUnknownCompanyIsNotFoundAndNothingIsSearched() {
        UUID missing = UUID.randomUUID();
        when(companies.findById(missing)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.companyDetail(userId, missing))
                .hasMessageContaining("Company not found");

        verify(search, never()).search(any());
        verify(search, never()).count(any());
    }
}
