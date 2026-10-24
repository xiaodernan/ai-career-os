package com.careeros.job.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.ai.AiServiceClient;
import com.careeros.application.service.ApplicationService;
import com.careeros.job.dto.JobDtos.CreateJobRequest;
import com.careeros.job.dto.JobDtos.ImportJobRequest;
import com.careeros.job.dto.JobDtos.JobListItem;
import com.careeros.job.entity.Company;
import com.careeros.job.entity.Job;
import com.careeros.job.repository.CompanyRepository;
import com.careeros.job.repository.JobJdRepository;
import com.careeros.job.repository.JobMatchRepository;
import com.careeros.job.repository.JobRepository;
import com.careeros.job.repository.JobSearchRepository;
import com.careeros.job.repository.SavedJobRepository;
import com.careeros.resume.service.ResumeService;
import com.careeros.search.service.QueryEmbeddingService;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.test.util.ReflectionTestUtils;

/**
 * The one field the reader supplies and the tracker does not decide: where the posting came from.
 *
 * Measured 2026-10-25 against the shipped code: the paste dialog sends {@code {rawText, url}}
 * ({@code frontend/src/components/jobs/import-job-dialog.tsx}) and {@code ImportJobRequest} carries
 * {@code url}, but {@code JobService.persistImport} filled {@code buildJob}'s external-url slot with a
 * literal {@code null} while {@code create} passes {@code request.externalUrl()}. So a reader who typed
 * the link to the job they pasted found nothing on the job's own page: the "original posting" link at
 * {@code frontend/src/app/(app)/jobs/[id]/page.tsx} renders only when {@code externalUrl} is set, and
 * {@code docs/SECURITY.md} records the field as "stored and displayed". Both job-creation paths are
 * asserted here because the slot is one parameter of one private builder, and a pass-through fixed on
 * one side only is the bug that is already here.
 *
 * <p>Plain Mockito, mirroring {@code JobServiceImportTest}: the write path is asserted through the
 * saved entity and the returned item, because the read path maps the same column.
 */
class JobServiceExternalUrlTest {

    private static final String PASTE = "Senior Backend Engineer - Agent Platform\nWe are hiring.";
    private static final String LINK = "https://boards.example.com/senior-backend-engineer";

    private final UUID userId = UUID.randomUUID();

    private JobRepository jobs;
    private CompanyRepository companies;
    private AiServiceClient ai;
    private JobService service;

    @BeforeEach
    void setUp() {
        jobs = mock(JobRepository.class);
        companies = mock(CompanyRepository.class);
        ai = mock(AiServiceClient.class);
        service = new JobService(jobs, companies, mock(JobJdRepository.class),
                mock(SavedJobRepository.class), mock(JobMatchRepository.class),
                mock(JobSearchRepository.class), mock(ResumeService.class),
                mock(ApplicationService.class), ai, mock(QueryEmbeddingService.class));
        when(jobs.save(any())).thenAnswer(inv -> {
            Job j = inv.getArgument(0);
            if (ReflectionTestUtils.getField(j, "id") == null) {
                ReflectionTestUtils.setField(j, "id", UUID.randomUUID());
            }
            return j;
        });
        // An unnamed company is created by the import, so the mock has to hand back a row with an id
        // the way the database does.
        when(companies.save(any())).thenAnswer(inv -> {
            Company c = inv.getArgument(0);
            if (ReflectionTestUtils.getField(c, "id") == null) {
                ReflectionTestUtils.setField(c, "id", UUID.randomUUID());
            }
            return c;
        });
    }

    private Job capturedJob() {
        ArgumentCaptor<Job> captor = ArgumentCaptor.forClass(Job.class);
        verify(jobs, times(1)).save(captor.capture());
        return captor.getValue();
    }

    private JobListItem importWith(String url, Map<String, Object> parsed) {
        Map<String, Object> answer = new HashMap<>();
        answer.put("parsed", parsed);
        when(ai.analyzeJd(any(), any())).thenReturn(answer);
        return service.importJob(userId, new ImportJobRequest(PASTE, url));
    }

    @Test
    void theImportPathStoresTheLinkTheReaderTypedBesideThePosting() {
        when(companies.findByName("Globex")).thenReturn(Optional.empty());

        JobListItem item = importWith(LINK, Map.of("title", "Senior Backend Engineer",
                "company", "Globex"));

        assertThat(capturedJob().getExternalUrl())
                .as("the import path stores the link the reader typed beside the posting")
                .isEqualTo(LINK);
        // The response is what the dialog navigates on, so the same slot has to be in it too.
        assertThat(item.externalUrl())
                .as("the import response carries the link, not only the row")
                .isEqualTo(LINK);
    }

    @Test
    void theCreatePathStoresTheSameSlotFromTheSameKindOfRequest() {
        UUID companyId = UUID.randomUUID();
        Company acme = new Company();
        acme.setName("Acme");
        ReflectionTestUtils.setField(acme, "id", companyId);
        when(companies.existsById(companyId)).thenReturn(true);
        when(companies.findById(companyId)).thenReturn(Optional.of(acme));

        JobListItem item = service.create(userId, new CreateJobRequest("Backend Engineer", companyId,
                null, "Remote", null, null, null, null, null, 5, "Building APIs.",
                List.of(), List.of(), List.of(), List.of(), null, LINK));

        assertThat(capturedJob().getExternalUrl())
                .as("the create path stores the same slot, so a one-sided pass-through is visible")
                .isEqualTo(LINK);
        assertThat(item.externalUrl())
                .as("the create response carries the link")
                .isEqualTo(LINK);
    }

    @Test
    void aPasteWithoutALinkLeavesTheSlotEmptyRatherThanInventingOne() {
        when(companies.findByName("Globex")).thenReturn(Optional.empty());

        JobListItem item = importWith(null, Map.of("title", "Senior Backend Engineer",
                "company", "Globex"));

        // The reader gave no address. The raw text is not one, and neither is a guess at where the
        // posting came from: an invented href sends the reader somewhere they never said.
        assertThat(capturedJob().getExternalUrl())
                .as("a paste with no link stays linkless rather than getting a substitute")
                .isNull();
        assertThat(item.externalUrl()).isNull();
    }

    @Test
    void theAnalystsAnswerCannotSupplyTheLinkTheReaderDidNot() {
        when(companies.findByName("Globex")).thenReturn(Optional.empty());

        // The parsed map is the model's own keys. It is not a source for a field the reader filled in
        // (or deliberately left empty), and a pass-through that read it would credit the model with
        // the reader's provenance.
        importWith(null, Map.of("title", "Senior Backend Engineer", "company", "Globex",
                "url", "https://model-guessed.example/job"));

        assertThat(capturedJob().getExternalUrl())
                .as("the reader sent no link, so the row carries none however the model answered")
                .isNull();
    }

    @Test
    void theImportKeepsThePostingTextAsItsOwnFieldNotAsTheLink() {
        when(companies.findByName("Globex")).thenReturn(Optional.empty());

        importWith(LINK, Map.of("title", "Senior Backend Engineer", "company", "Globex"));

        Job job = capturedJob();
        assertThat(job.getDescription()).isEqualTo(PASTE);
        assertThat(job.getExternalUrl())
                .as("the link is its own column, not a copy of the posting text")
                .isEqualTo(LINK);
    }
}
