package com.careeros.job.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.ai.AiServiceClient;
import com.careeros.job.dto.JobDtos.SavedJobItem;
import com.careeros.job.entity.Company;
import com.careeros.job.entity.Job;
import com.careeros.job.entity.SavedJob;
import com.careeros.job.repository.CompanyRepository;
import com.careeros.job.repository.JobJdRepository;
import com.careeros.job.repository.JobMatchRepository;
import com.careeros.job.repository.JobRepository;
import com.careeros.job.repository.JobSearchRepository;
import com.careeros.job.repository.SavedJobRepository;
import com.careeros.resume.service.ResumeService;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

/**
 * The saved-jobs list must resolve its rows in a fixed number of queries.
 *
 * <p>Regression guard for a real N+1 (PRD §36 calls it out explicitly): the list used to call
 * {@code jobs.findById} and {@code companies.findById} inside its map, so N bookmarks cost
 * 1 + 2N queries. Plain Mockito — no DB, no Spring context — so the query count is asserted
 * directly rather than inferred from timing.
 */
class JobServiceSavedTest {

    private final UUID userId = UUID.randomUUID();

    private JobRepository jobs;
    private CompanyRepository companies;
    private SavedJobRepository savedJobs;
    private JobService service;

    @BeforeEach
    void setUp() {
        jobs = mock(JobRepository.class);
        companies = mock(CompanyRepository.class);
        savedJobs = mock(SavedJobRepository.class);
        service = new JobService(jobs, companies, mock(JobJdRepository.class), savedJobs,
                mock(JobMatchRepository.class), mock(JobSearchRepository.class),
                mock(ResumeService.class), mock(AiServiceClient.class));
    }

    private static Job job(UUID id, String title, UUID companyId) {
        Job j = new Job();
        ReflectionTestUtils.setField(j, "id", id);
        j.setTitle(title);
        j.setCompanyId(companyId);
        return j;
    }

    private static Company company(UUID id, String name) {
        Company c = new Company();
        ReflectionTestUtils.setField(c, "id", id);
        c.setName(name);
        return c;
    }

    private static SavedJob saved(UUID jobId, String note) {
        SavedJob s = new SavedJob();
        s.setJobId(jobId);
        s.setNote(note);
        return s;
    }

    @Test
    void resolvesEveryRowWithOneJobQueryAndOneCompanyQuery() {
        UUID acme = UUID.randomUUID();
        UUID globex = UUID.randomUUID();
        UUID j1 = UUID.randomUUID();
        UUID j2 = UUID.randomUUID();
        UUID j3 = UUID.randomUUID();

        when(savedJobs.findByUserIdOrderByCreatedAtDesc(userId))
                .thenReturn(List.of(saved(j1, "a"), saved(j2, "b"), saved(j3, "c")));
        when(jobs.findAllById(any())).thenReturn(List.of(
                job(j1, "Backend Engineer", acme),
                job(j2, "Data Engineer", globex),
                job(j3, "SRE", acme)));
        when(companies.findAllById(any())).thenReturn(List.of(
                company(acme, "Acme"), company(globex, "Globex")));

        List<SavedJobItem> out = service.saved(userId);

        assertThat(out).hasSize(3);
        assertThat(out).extracting(i -> i.job().title())
                .containsExactly("Backend Engineer", "Data Engineer", "SRE");
        assertThat(out).extracting(i -> i.job().companyName())
                .containsExactly("Acme", "Globex", "Acme");
        assertThat(out).extracting(SavedJobItem::note).containsExactly("a", "b", "c");

        // The point of the test: batched, and never per-row.
        verify(jobs, times(1)).findAllById(any());
        verify(companies, times(1)).findAllById(any());
        verify(jobs, never()).findById(any());
        verify(companies, never()).findById(any());
    }

    @Test
    void queryCountDoesNotGrowWithTheNumberOfBookmarks() {
        UUID companyId = UUID.randomUUID();
        UUID[] ids = {UUID.randomUUID(), UUID.randomUUID(), UUID.randomUUID(), UUID.randomUUID(),
                UUID.randomUUID(), UUID.randomUUID(), UUID.randomUUID(), UUID.randomUUID()};

        when(savedJobs.findByUserIdOrderByCreatedAtDesc(userId))
                .thenReturn(java.util.Arrays.stream(ids).map(id -> saved(id, null)).toList());
        when(jobs.findAllById(any()))
                .thenReturn(java.util.Arrays.stream(ids).map(id -> job(id, "Role", companyId)).toList());
        when(companies.findAllById(any())).thenReturn(List.of(company(companyId, "Acme")));

        assertThat(service.saved(userId)).hasSize(8);

        // Eight rows, still exactly one lookup per table.
        verify(jobs, times(1)).findAllById(any());
        verify(companies, times(1)).findAllById(any());
    }

    @Test
    void anEmptyListDoesNotTouchTheJobOrCompanyTables() {
        when(savedJobs.findByUserIdOrderByCreatedAtDesc(userId)).thenReturn(List.of());

        assertThat(service.saved(userId)).isEmpty();

        verify(jobs, never()).findAllById(any());
        verify(companies, never()).findAllById(any());
    }

    @Test
    void aBookmarkWhoseJobWasDeletedIsSkippedRatherThanFailingTheList() {
        UUID j1 = UUID.randomUUID();
        UUID j2 = UUID.randomUUID();
        when(savedJobs.findByUserIdOrderByCreatedAtDesc(userId))
                .thenReturn(List.of(saved(j1, "kept"), saved(j2, "orphan")));
        when(jobs.findAllById(any())).thenReturn(List.of(job(j1, "Backend Engineer", null)));
        when(companies.findAllById(any())).thenReturn(List.of());

        List<SavedJobItem> out = service.saved(userId);

        assertThat(out).hasSize(1);
        assertThat(out.get(0).job().title()).isEqualTo("Backend Engineer");
        // A missing company must not null the name out.
        assertThat(out.get(0).job().companyName()).isEmpty();
    }
}
