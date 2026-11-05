package com.careeros.application.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.application.dto.ApplicationDtos.ApplicationPacket;
import com.careeros.application.entity.Application;
import com.careeros.application.repository.ApplicationLetterRepository;
import com.careeros.interview.entity.InterviewEvaluation;
import com.careeros.interview.repository.InterviewEvaluationRepository;
import com.careeros.interview.repository.InterviewSessionRepository;
import com.careeros.job.entity.Company;
import com.careeros.job.entity.Job;
import com.careeros.job.entity.JobJd;
import com.careeros.job.entity.JobMatch;
import com.careeros.job.repository.CompanyRepository;
import com.careeros.job.repository.JobJdRepository;
import com.careeros.job.repository.JobMatchRepository;
import com.careeros.job.repository.JobRepository;
import com.careeros.resume.entity.Resume;
import com.careeros.resume.entity.ResumeVersion;
import com.careeros.resume.repository.ResumeRepository;
import com.careeros.resume.repository.ResumeVersionRepository;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/**
 * The packet is the application's three links made readable. The distinction this pins is the
 * one a reader needs: a missing column and a link whose row can no longer be read are different
 * facts, and neither may become another account's title.
 */
class ApplicationPacketServiceTest {

    private final UUID userId = UUID.randomUUID();
    private final UUID applicationId = UUID.randomUUID();
    private final UUID resumeVersionId = UUID.randomUUID();
    private final UUID jdId = UUID.randomUUID();
    private final UUID matchId = UUID.randomUUID();
    private final UUID jobId = UUID.randomUUID();

    private ApplicationService applications;
    private ResumeVersionRepository resumeVersions;
    private ResumeRepository resumes;
    private JobJdRepository jds;
    private JobMatchRepository matches;
    private JobRepository jobs;
    private CompanyRepository companies;
    private ApplicationLetterRepository letters;
    private InterviewSessionRepository interviews;
    private InterviewEvaluationRepository evaluations;
    private ApplicationPacketService service;
    private Application app;

    @BeforeEach
    void setUp() {
        applications = mock(ApplicationService.class);
        resumeVersions = mock(ResumeVersionRepository.class);
        resumes = mock(ResumeRepository.class);
        jds = mock(JobJdRepository.class);
        matches = mock(JobMatchRepository.class);
        jobs = mock(JobRepository.class);
        companies = mock(CompanyRepository.class);
        letters = mock(ApplicationLetterRepository.class);
        interviews = mock(InterviewSessionRepository.class);
        evaluations = mock(InterviewEvaluationRepository.class);
        service = new ApplicationPacketService(applications, resumeVersions, resumes, jds,
                matches, jobs, companies, letters, interviews, evaluations);

        app = mock(Application.class);
        when(app.getId()).thenReturn(applicationId);
        when(applications.require(userId, applicationId)).thenReturn(app);
        when(letters.countByApplicationIdAndUserId(applicationId, userId)).thenReturn(2L);
        when(interviews.countByApplicationIdAndUserId(applicationId, userId)).thenReturn(1L);
        when(evaluations.findForApplication(userId, applicationId)).thenReturn(List.of());
    }

    @Test
    void resolvesEveryLinkedArtifactToTheLabelsAReaderCanCheck() {
        when(app.getResumeVersionId()).thenReturn(resumeVersionId);
        when(app.getJdId()).thenReturn(jdId);
        when(app.getMatchId()).thenReturn(matchId);

        ResumeVersion version = mock(ResumeVersion.class);
        when(version.getId()).thenReturn(resumeVersionId);
        when(version.getResumeId()).thenReturn(UUID.randomUUID());
        when(version.getLabel()).thenReturn("Backend tailored");
        when(version.getKind()).thenReturn("tailored");
        when(version.getCreatedAt()).thenReturn(OffsetDateTime.parse("2026-10-01T09:00:00Z"));
        when(resumeVersions.findByIdAndUserId(resumeVersionId, userId))
                .thenReturn(Optional.of(version));
        Resume resume = mock(Resume.class);
        when(resume.getTitle()).thenReturn("Ada Lovelace resume");
        when(resumes.findByIdAndUserId(version.getResumeId(), userId)).thenReturn(Optional.of(resume));

        Job job = mock(Job.class);
        when(job.getTitle()).thenReturn("Staff Backend Engineer");
        when(job.getCompanyId()).thenReturn(UUID.randomUUID());
        when(jobs.findById(jobId)).thenReturn(Optional.of(job));
        Company company = mock(Company.class);
        when(company.getName()).thenReturn("Northwind");
        when(companies.findById(job.getCompanyId())).thenReturn(Optional.of(company));
        JobJd analysis = mock(JobJd.class);
        when(analysis.getId()).thenReturn(jdId);
        when(analysis.getJobId()).thenReturn(jobId);
        when(analysis.getParsed()).thenReturn(Map.of(
                "title", "Backend Platform Engineer", "company", "Northwind Labs"));
        when(jds.findByIdAndUserId(jdId, userId)).thenReturn(Optional.of(analysis));

        JobMatch match = mock(JobMatch.class);
        when(match.getId()).thenReturn(matchId);
        when(match.getJobId()).thenReturn(jobId);
        when(match.getOverall()).thenReturn(0.82f);
        when(matches.findByIdAndUserId(matchId, userId)).thenReturn(Optional.of(match));

        ApplicationPacket packet = service.packet(userId, applicationId);

        assertThat(packet.applicationId()).isEqualTo(applicationId);
        assertThat(packet.resumeLinked()).isTrue();
        assertThat(packet.resume()).isNotNull();
        assertThat(packet.resume().title()).isEqualTo("Ada Lovelace resume");
        assertThat(packet.resume().label()).isEqualTo("Backend tailored");
        assertThat(packet.resume().kind()).isEqualTo("tailored");
        assertThat(packet.jdLinked()).isTrue();
        assertThat(packet.jd().title()).isEqualTo("Backend Platform Engineer");
        assertThat(packet.jd().companyName()).isEqualTo("Northwind Labs");
        assertThat(packet.matchLinked()).isTrue();
        assertThat(packet.match().overall()).isEqualTo(0.82f);
        assertThat(packet.match().jobId()).isEqualTo(jobId);
        assertThat(packet.letters()).isEqualTo(2);
        assertThat(packet.rehearsals()).isEqualTo(1);
    }

    @Test
    void aLinkWhoseRowIsNotTheCallersStaysLinkedButHasNoValue() {
        when(app.getResumeVersionId()).thenReturn(resumeVersionId);
        when(app.getJdId()).thenReturn(jdId);
        when(app.getMatchId()).thenReturn(matchId);
        when(resumeVersions.findByIdAndUserId(resumeVersionId, userId)).thenReturn(Optional.empty());
        when(jds.findByIdAndUserId(jdId, userId)).thenReturn(Optional.empty());
        when(matches.findByIdAndUserId(matchId, userId)).thenReturn(Optional.empty());

        ApplicationPacket packet = service.packet(userId, applicationId);

        assertThat(packet.resumeLinked()).isTrue();
        assertThat(packet.resume()).isNull();
        assertThat(packet.jdLinked()).isTrue();
        assertThat(packet.jd()).isNull();
        assertThat(packet.matchLinked()).isTrue();
        assertThat(packet.match()).isNull();
        // Every read is user-scoped. An id that belongs to another account is indistinguishable
        // from one that no longer exists, which is the only safe answer for a lookup by uuid.
        verify(resumeVersions).findByIdAndUserId(resumeVersionId, userId);
        verify(jds).findByIdAndUserId(jdId, userId);
        verify(matches).findByIdAndUserId(matchId, userId);
    }

    @Test
    void nothingLinkedMeansNoLookupsAtAll() {
        when(app.getResumeVersionId()).thenReturn(null);
        when(app.getJdId()).thenReturn(null);
        when(app.getMatchId()).thenReturn(null);

        ApplicationPacket packet = service.packet(userId, applicationId);

        assertThat(packet.resumeLinked()).isFalse();
        assertThat(packet.jdLinked()).isFalse();
        assertThat(packet.matchLinked()).isFalse();
        verify(resumeVersions, never()).findByIdAndUserId(org.mockito.ArgumentMatchers.any(),
                org.mockito.ArgumentMatchers.any());
        verify(jds, never()).findByIdAndUserId(org.mockito.ArgumentMatchers.any(),
                org.mockito.ArgumentMatchers.any());
        verify(matches, never()).findByIdAndUserId(org.mockito.ArgumentMatchers.any(),
                org.mockito.ArgumentMatchers.any());
    }

    /**
     * The fourth artifact is a count rather than a link, and the count has to be this caller's:
     * the query names both the application and the user, so a stray row can never be reported as
     * this card's letter.
     */
    @Test
    void theLetterCountIsScopedToTheApplicationAndTheCaller() {
        when(app.getResumeVersionId()).thenReturn(null);
        when(app.getJdId()).thenReturn(null);
        when(app.getMatchId()).thenReturn(null);
        when(letters.countByApplicationIdAndUserId(applicationId, userId)).thenReturn(3L);

        ApplicationPacket packet = service.packet(userId, applicationId);

        assertThat(packet.letters()).isEqualTo(3);
        verify(letters).countByApplicationIdAndUserId(applicationId, userId);
    }

    @Test
    void theRehearsalCountIsScopedToTheApplicationAndTheCallerToo() {
        // 57.2: the fifth row is what came back from the practice, so it is
        // counted the same way the letters are -- the card and the caller
        // together, never the card alone.
        when(app.getResumeVersionId()).thenReturn(null);
        when(app.getJdId()).thenReturn(null);
        when(app.getMatchId()).thenReturn(null);
        when(interviews.countByApplicationIdAndUserId(applicationId, userId)).thenReturn(4L);

        ApplicationPacket packet = service.packet(userId, applicationId);

        assertThat(packet.rehearsals()).isEqualTo(4);
        verify(interviews).countByApplicationIdAndUserId(applicationId, userId);
    }

    /**
     * 59.2: the row also says how the practice went. Every graded rehearsal on the card is a
     * candidate and the highest wins -- a second attempt that scored lower does not drag the
     * best down, which is the number a reader deciding whether to rehearse again wants.
     */
    @Test
    void theBestScoreIsTheHighestGradedRehearsalOnTheCard() {
        when(app.getResumeVersionId()).thenReturn(null);
        when(app.getJdId()).thenReturn(null);
        when(app.getMatchId()).thenReturn(null);
        when(interviews.countByApplicationIdAndUserId(applicationId, userId)).thenReturn(3L);
        // Built before the stub: Mockito refuses a mock being stubbed inside another
        // `when(...)` argument.
        InterviewEvaluation first = evaluationWith(0.62);
        InterviewEvaluation best = evaluationWith(0.84);
        InterviewEvaluation third = evaluationWith(0.71);
        when(evaluations.findForApplication(userId, applicationId))
                .thenReturn(List.of(first, best, third));

        ApplicationPacket packet = service.packet(userId, applicationId);

        assertThat(packet.rehearsals()).isEqualTo(3);
        assertThat(packet.bestRehearsalScore()).isEqualTo(0.84f);
        verify(evaluations).findForApplication(userId, applicationId);
    }

    /**
     * A rehearsal that never finished has no evaluation row, so a card with practice but no
     * grades has no best score -- and that is null, not zero: "no result yet" and "scored
     * zero" are different things to show beside the count.
     */
    @Test
    void practiceWithoutAGradeHasNoBestScore() {
        when(app.getResumeVersionId()).thenReturn(null);
        when(app.getJdId()).thenReturn(null);
        when(app.getMatchId()).thenReturn(null);
        when(interviews.countByApplicationIdAndUserId(applicationId, userId)).thenReturn(2L);
        when(evaluations.findForApplication(userId, applicationId)).thenReturn(List.of());

        ApplicationPacket packet = service.packet(userId, applicationId);

        assertThat(packet.rehearsals()).isEqualTo(2);
        assertThat(packet.bestRehearsalScore()).isNull();
    }

    @Test
    void aCardNobodyPractisedForAsksTheEvaluatorNothing() {
        when(app.getResumeVersionId()).thenReturn(null);
        when(app.getJdId()).thenReturn(null);
        when(app.getMatchId()).thenReturn(null);
        when(interviews.countByApplicationIdAndUserId(applicationId, userId)).thenReturn(0L);

        ApplicationPacket packet = service.packet(userId, applicationId);

        assertThat(packet.rehearsals()).isZero();
        assertThat(packet.bestRehearsalScore()).isNull();
        verify(evaluations, never()).findForApplication(userId, applicationId);
    }

    private static InterviewEvaluation evaluationWith(double overall) {
        InterviewEvaluation evaluation = mock(InterviewEvaluation.class);
        when(evaluation.getSummary()).thenReturn(Map.of("overall", overall));
        return evaluation;
    }
}
