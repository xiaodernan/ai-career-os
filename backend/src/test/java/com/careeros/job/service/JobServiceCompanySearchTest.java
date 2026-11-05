package com.careeros.job.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.ai.AiServiceClient;
import com.careeros.application.service.ApplicationService;
import com.careeros.job.dto.JobDtos.CompanyItem;
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
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.test.util.ReflectionTestUtils;

/**
 * The company board's search reads the reader's words once, in one spelling (58.1).
 *
 * <p>{@code CompanyNeedleIT} proves what the database does with a percent sign, but it needs the
 * Docker-hosted Postgres and so cannot run on every machine. This is the half that can: the service
 * is where the needle is trimmed, lower-cased and sent to the one query that has no pattern
 * language -- and where a blank box has to stay the browse rather than becoming a search for
 * spaces.
 *
 * <p>The case defect the old spelling carried is invisible to a mocked repository unless the
 * argument is asserted: an integration run found nothing for a literal {@code Per%cent} because the
 * needle was lower-cased while the SQL compared it to a mixed-case column with a case-sensitive
 * {@code LIKE}. The {@code LOWER(c.name)} half lives in the JPQL and
 * {@code SearchNeedleContractTest} pins it; what this file pins is that the value arriving at the
 * query is the form that JPQL expects.
 */
class JobServiceCompanySearchTest {

    private static final String NEEDLE = "star sea";

    private CompanyRepository companies;
    private JobService service;

    @BeforeEach
    void setUp() {
        companies = mock(CompanyRepository.class);
        when(companies.openRoleCounts()).thenReturn(List.of());
        service = new JobService(mock(JobRepository.class), companies, mock(JobJdRepository.class),
                mock(SavedJobRepository.class), mock(JobMatchRepository.class),
                mock(JobSearchRepository.class), mock(ResumeService.class),
                mock(ApplicationService.class), mock(AiServiceClient.class),
                mock(QueryEmbeddingService.class), TestTransactions.executing());
    }

    private Company company(String name) {
        Company company = new Company();
        ReflectionTestUtils.setField(company, "id", UUID.randomUUID());
        company.setName(name);
        return company;
    }

    @Test
    @DisplayName("a typed needle reaches the LOCATE query trimmed and lower-cased, once")
    void theNeedleArrivesInTheFormTheQueryExpects() {
        Company starSea = company("Star Sea");
        when(companies.searchByName(eq(NEEDLE), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(starSea), PageRequest.of(0, 20), 1));

        var page = service.listCompanies("  Star SEA  ", 0, 20);

        verify(companies).searchByName(eq(NEEDLE), any(Pageable.class));
        verify(companies, never()).findAllByOrderByNameAsc(any());
        assertThat(page.items()).extracting(CompanyItem::name).containsExactly("Star Sea");
        assertThat(page.total()).isEqualTo(1);
    }

    @Test
    @DisplayName("a blank box is the unfiltered browse, and it never becomes a search for spaces")
    void aBlankBoxTakesTheBrowseBranch() {
        when(companies.findAllByOrderByNameAsc(any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(company("Anywhere")), PageRequest.of(0, 20), 1));

        service.listCompanies(null, 0, 20);
        service.listCompanies("", 0, 20);
        service.listCompanies("   ", 0, 20);

        verify(companies, times(3)).findAllByOrderByNameAsc(any());
        verify(companies, never()).searchByName(any(), any());
    }

    @Test
    @DisplayName("the searched page's open-role counts still come from the one grouped read")
    void theSearchedPageCarriesTheOpenRoleCounts() {
        Company starSea = company("Star Sea");
        when(companies.searchByName(eq(NEEDLE), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(starSea), PageRequest.of(0, 20), 1));
        when(companies.openRoleCounts())
                .thenReturn(List.<Object[]>of(new Object[] {starSea.getId(), 3L}));

        var page = service.listCompanies(NEEDLE, 0, 20);

        assertThat(page.items()).extracting(CompanyItem::openRoleCount).containsExactly(3L);
    }
}
