package com.careeros.job.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.ai.AiServiceClient;
import com.careeros.application.service.ApplicationService;
import com.careeros.job.dto.JobDtos.JobListItem;
import com.careeros.job.dto.JobDtos.SavedJobItem;
import com.careeros.job.repository.CompanyRepository;
import com.careeros.job.repository.JobJdRepository;
import com.careeros.job.repository.JobMatchRepository;
import com.careeros.job.repository.JobRepository;
import com.careeros.job.repository.JobSearchRepository;
import com.careeros.job.repository.JobSearchRepository.SavedBoard;
import com.careeros.job.repository.JobSearchRepository.SavedRow;
import com.careeros.job.repository.SavedJobRepository;
import com.careeros.resume.service.ResumeService;
import com.careeros.search.service.QueryEmbeddingService;
import com.careeros.support.TestTransactions;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

/**
 * The saved-jobs read is one statement and this service adds nothing to it.
 *
 * <p>The guard this replaces was real: N bookmarks used to cost 1 + 2N queries, because the list
 * called {@code jobs.findById} and {@code companies.findById} inside its map (PRD section 36 calls
 * N+1 out explicitly). Fixing it by batching left a second defect -- a read that answered no
 * predicates at all, so the browser kept its own copy of which rows match and that copy drifted
 * from the server's (74.1). One join answers both, and the row repositories the batch needed are
 * now not reachable from this path, which is what the second case asserts instead of a count.
 *
 * <p>Which rows match is a database question, and {@code SavedJobBoardIT} answers it against real
 * Postgres. Plain Mockito here answers the shape question: what the read is handed, and whether the
 * answer survives the trip through the service.
 */
class JobServiceSavedTest {

    private final UUID userId = UUID.randomUUID();

    private JobRepository jobs;
    private CompanyRepository companies;
    private SavedJobRepository savedJobs;
    private JobSearchRepository search;
    private JobService service;

    @BeforeEach
    void setUp() {
        jobs = mock(JobRepository.class);
        companies = mock(CompanyRepository.class);
        savedJobs = mock(SavedJobRepository.class);
        search = mock(JobSearchRepository.class);
        service = new JobService(jobs, companies, mock(JobJdRepository.class), savedJobs,
                mock(JobMatchRepository.class), search,
                mock(ResumeService.class), mock(ApplicationService.class),
                mock(AiServiceClient.class), mock(QueryEmbeddingService.class),
                TestTransactions.executing());
    }

    private static SavedRow row(String title, String note) {
        JobListItem job = new JobListItem(UUID.randomUUID(), title, UUID.randomUUID(), "Acme",
                "Hangzhou", "remote", "full_time", 400000, 500000, "CNY", 5, "active", "manual",
                null, OffsetDateTime.parse("2026-01-02T03:04:05Z"), List.of("java"), null, null);
        return new SavedRow(job, note, OffsetDateTime.parse("2026-01-03T04:05:06Z"));
    }

    @Test
    void answersEveryRowTheReadReturnedInExactlyThatOrder() {
        when(search.saved(any(SavedBoard.class)))
                .thenReturn(List.of(row("Backend Engineer", "a"), row("Data Engineer", "b"),
                        row("SRE", "c")));

        List<SavedJobItem> out = service.saved(userId, "java", List.of("spring"), "Remote",
                "remote", "Acme", 40, 80);

        assertThat(out).extracting(i -> i.job().title())
                .containsExactly("Backend Engineer", "Data Engineer", "SRE");
        assertThat(out).extracting(SavedJobItem::note).containsExactly("a", "b", "c");
        // The read's own ordering is the answer's ordering; a service that sorted, filtered or
        // dropped rows here would be a second, drifting copy of the board's logic.
        assertThat(out).allSatisfy(i -> assertThat(i.job().companyName()).isEqualTo("Acme"));
        assertThat(out).allSatisfy(i -> assertThat(i.savedAt())
                .isEqualTo(OffsetDateTime.parse("2026-01-03T04:05:06Z")));
    }

    @Test
    void noBookmarkJobOrCompanyRepositoryIsReachableFromTheList() {
        when(search.saved(any(SavedBoard.class))).thenReturn(List.of(row("SRE", null)));

        service.saved(userId, null, null, null, null, null, null, null);

        // The batch this replaces needed findAllById on both tables; the join needs neither. Any
        // per-row path back through these mocks -- findById, findAllById, or the bookmark scan the
        // old version started from -- is the N+1 coming back.
        verify(jobs, never()).findById(any());
        verify(jobs, never()).findAllById(any());
        verify(companies, never()).findById(any());
        verify(companies, never()).findAllById(any());
        verify(savedJobs, never()).findByUserIdOrderByCreatedAtDesc(any());
        verify(savedJobs, never()).findAll();
    }

    @Test
    void thePanelsWholeSetOfPredicatesRidesToTheReadUntouched() {
        when(search.saved(any(SavedBoard.class))).thenReturn(List.of());
        List<String> skills = List.of("spring", "kafka");

        service.saved(userId, "java", skills, "Remote", "hybrid", "Acme", 40, 80);

        ArgumentCaptor<SavedBoard> board = ArgumentCaptor.forClass(SavedBoard.class);
        verify(search).saved(board.capture());
        assertThat(board.getValue().userId()).isEqualTo(userId);
        assertThat(board.getValue().q()).isEqualTo("java");
        assertThat(board.getValue().skills()).isEqualTo(skills);
        assertThat(board.getValue().location()).isEqualTo("Remote");
        assertThat(board.getValue().remote()).isEqualTo("hybrid");
        assertThat(board.getValue().company()).isEqualTo("Acme");
        assertThat(board.getValue().minSalary()).isEqualTo(40);
        assertThat(board.getValue().maxSalary()).isEqualTo(80);
    }

    @Test
    void aBoxNobodyTypedIsHandedToTheReadAsNothingRatherThanAsAWildcard() {
        when(search.saved(any(SavedBoard.class))).thenReturn(List.of());

        service.saved(userId, null, null, null, null, null, null, null);

        ArgumentCaptor<SavedBoard> board = ArgumentCaptor.forClass(SavedBoard.class);
        verify(search).saved(board.capture());
        // Null in, null out. Substituting "" here would reach the SQL as a search for the empty
        // string, and a needle of "" is a filter the reader never asked for.
        assertThat(board.getValue().q()).isNull();
        assertThat(board.getValue().skills()).isNull();
        assertThat(board.getValue().minSalary()).isNull();
    }

    @Test
    void anEmptyShelfAnswersEmptyWithoutReachingForTheRowTables() {
        when(search.saved(any(SavedBoard.class))).thenReturn(List.of());

        assertThat(service.saved(userId, "java", List.of(), "Remote", null, null, null, null))
                .isEmpty();

        verify(jobs, never()).findAllById(any());
        verify(companies, never()).findAllById(any());
    }
}
