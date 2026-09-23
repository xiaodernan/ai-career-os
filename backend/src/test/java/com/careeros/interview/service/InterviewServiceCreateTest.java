package com.careeros.interview.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.ai.AiServiceClient;
import com.careeros.interview.dto.InterviewDtos.CreateSessionRequest;
import com.careeros.interview.entity.InterviewSession;
import com.careeros.interview.repository.InterviewEvaluationRepository;
import com.careeros.interview.repository.InterviewSessionRepository;
import com.careeros.interview.repository.InterviewTurnRepository;
import com.careeros.job.entity.Company;
import com.careeros.job.entity.Job;
import com.careeros.job.repository.CompanyRepository;
import com.careeros.job.repository.JobRepository;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

/**
 * A session started from a job page arrives with nothing but {@code job_id}: the UI sends no
 * role text, so unless the service copies it off the job the row is born with NULL
 * company_name / position_title and every screen that names the practice target is blank.
 */
class InterviewServiceCreateTest {

    private final UUID userId = UUID.randomUUID();
    private final UUID jobId = UUID.randomUUID();
    private final UUID companyId = UUID.randomUUID();

    private InterviewSessionRepository sessions;
    private JobRepository jobs;
    private CompanyRepository companies;
    private InterviewService service;

    @BeforeEach
    void setUp() {
        sessions = mock(InterviewSessionRepository.class);
        jobs = mock(JobRepository.class);
        companies = mock(CompanyRepository.class);
        service = new InterviewService(sessions, mock(InterviewTurnRepository.class),
                mock(InterviewEvaluationRepository.class), jobs, companies,
                mock(AiServiceClient.class));
        when(sessions.save(any(InterviewSession.class))).thenAnswer(i -> i.getArgument(0));
    }

    private void givenJob() {
        Job job = new Job();
        job.setCompanyId(companyId);
        job.setTitle("Staff Backend Engineer");
        when(jobs.findById(jobId)).thenReturn(Optional.of(job));
        Company company = new Company();
        company.setName("ACME GmbH");
        when(companies.findById(companyId)).thenReturn(Optional.of(company));
    }

    private InterviewSession saved() {
        ArgumentCaptor<InterviewSession> cap = ArgumentCaptor.forClass(InterviewSession.class);
        verify(sessions).save(cap.capture());
        return cap.getValue();
    }

    private CreateSessionRequest request(String companyName, String positionTitle) {
        return new CreateSessionRequest(jobId, null, null, companyName, positionTitle, "technical", null);
    }

    @Test
    void jobOnlyRequestStillRecordsWhatTheInterviewIsFor() {
        givenJob();

        service.create(userId, request(null, null));

        InterviewSession s = saved();
        assertThat(s.getPositionTitle()).isEqualTo("Staff Backend Engineer");
        assertThat(s.getCompanyName()).isEqualTo("ACME GmbH");
        assertThat(s.getJobId()).isEqualTo(jobId);
        assertThat(s.getMode()).isEqualTo("technical");
    }

    @Test
    void blankTextCountsAsMissingAndTheJobFillsIt() {
        givenJob();

        service.create(userId, request("   ", ""));

        InterviewSession s = saved();
        assertThat(s.getPositionTitle()).isEqualTo("Staff Backend Engineer");
        assertThat(s.getCompanyName()).isEqualTo("ACME GmbH");
    }

    @Test
    void explicitTextWinsOverTheJob() {
        givenJob();

        service.create(userId, request("Freelance", "Senior Platform Engineer"));

        InterviewSession s = saved();
        assertThat(s.getPositionTitle()).isEqualTo("Senior Platform Engineer");
        assertThat(s.getCompanyName()).isEqualTo("Freelance");
    }

    @Test
    void freeTextSessionWithoutAJobSkipsTheLookup() {
        service.create(userId, new CreateSessionRequest(null, null, null,
                "Self-employed", "Own project", "behavioral", null));

        verify(jobs, never()).findById(any());
        InterviewSession s = saved();
        assertThat(s.getCompanyName()).isEqualTo("Self-employed");
        assertThat(s.getPositionTitle()).isEqualTo("Own project");
    }

    @Test
    void aMissingJobRowDoesNotBreakSessionCreation() {
        when(jobs.findById(jobId)).thenReturn(Optional.empty());

        service.create(userId, request(null, null));

        InterviewSession s = saved();
        assertThat(s.getJobId()).isEqualTo(jobId);
        assertThat(s.getPositionTitle()).isNull();
        // Columns that are nullable stay null rather than inventing a placeholder.
        verify(companies, never()).findById(any());
    }
}
