package com.careeros.job.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import com.careeros.ai.AiServiceClient;
import com.careeros.application.service.ApplicationService;
import com.careeros.job.entity.Job;
import com.careeros.job.entity.JobJd;
import com.careeros.job.repository.CompanyRepository;
import com.careeros.job.repository.JobJdRepository;
import com.careeros.job.repository.JobMatchRepository;
import com.careeros.job.repository.JobRepository;
import com.careeros.job.repository.JobSearchRepository;
import com.careeros.job.repository.SavedJobRepository;
import com.careeros.resume.entity.Resume;
import com.careeros.resume.service.ResumeService;
import com.careeros.search.service.QueryEmbeddingService;
import com.careeros.support.TestTransactions;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

/**
 * The three routes that mint a link id have to hand it to the tracker: a match names the resume it
 * measured and the match row it stored, tailoring names the resume the draft came from, and a JD
 * analysis names the analysis it just saved.
 *
 * <p>This is the half no browser test can see. The card renders whatever the {@code ApplicationItem}
 * carries, so an id the service never links is a card that shows nothing — and the ids are minted
 * here, two services away from the write that stores them.
 */
class JobServiceLinkTest {

    private final UUID userId = UUID.randomUUID();
    private final UUID jobId = UUID.randomUUID();

    private JobRepository jobs;
    private JobJdRepository jds;
    private AiServiceClient ai;
    private ApplicationService applicationService;
    private JobService service;

    @BeforeEach
    void setUp() {
        jobs = mock(JobRepository.class);
        jds = mock(JobJdRepository.class);
        ai = mock(AiServiceClient.class);
        applicationService = mock(ApplicationService.class);
        service = new JobService(jobs, mock(CompanyRepository.class), jds,
                mock(SavedJobRepository.class), mock(JobMatchRepository.class),
                mock(JobSearchRepository.class), mock(ResumeService.class), applicationService,
                ai, mock(QueryEmbeddingService.class), TestTransactions.executing());
        Job job = new Job();
        ReflectionTestUtils.setField(job, "id", jobId);
        when(jobs.findById(jobId)).thenReturn(Optional.of(job));
    }

    @Test
    void aMatchLinksTheResumeItMeasuredAndTheMatchItStored() {
        UUID resumeVersionId = UUID.randomUUID();
        UUID matchId = UUID.randomUUID();
        Map<String, Object> answer = new HashMap<>();
        answer.put("match", Map.of("overall", 0.8));
        answer.put("match_id", matchId.toString());
        when(ai.matchJob(jobId, resumeVersionId, userId)).thenReturn(answer);

        service.match(userId, jobId, resumeVersionId);

        verify(applicationService).linkJobActivity(userId, jobId, resumeVersionId, null, matchId);
    }

    @Test
    void aMatchTheAiServiceCouldNotNameStillLinksTheResume() {
        // `match_id` is read off ai-service's answer, and an answer without one used to be a match
        // card with no stored row to open. The resume is still a link, and null must mean "leave the
        // column alone" rather than "clear it".
        UUID resumeVersionId = UUID.randomUUID();
        when(ai.matchJob(jobId, resumeVersionId, userId)).thenReturn(new HashMap<>(Map.of(
                "match", Map.of("overall", 0.5))));

        service.match(userId, jobId, resumeVersionId);

        verify(applicationService).linkJobActivity(userId, jobId, resumeVersionId, null, null);
    }

    @Test
    void tailoringLinksTheResumeTheDraftCameFrom() {
        UUID resumeVersionId = UUID.randomUUID();
        when(ai.tailorResume(jobId, resumeVersionId, userId)).thenReturn(Map.of("tailored", Map.of()));

        service.tailor(userId, jobId, resumeVersionId);

        verify(applicationService).linkJobActivity(userId, jobId, resumeVersionId, null, null);
    }

    @Test
    void aJobScopedJdAnalysisLinksTheRowItSaved() {
        JobJd saved = new JobJd();
        UUID jdId = UUID.randomUUID();
        ReflectionTestUtils.setField(saved, "id", jdId);
        when(ai.analyzeJd("raw jd", userId)).thenReturn(new HashMap<>(Map.of("parsed", Map.of())));
        when(jds.save(any(JobJd.class))).thenReturn(saved);

        assertThat(service.analyzeJd(userId, "raw jd", jobId).getId()).isEqualTo(jdId);

        // The id in the link is the saved row's, not a value the caller passed in.
        verify(applicationService).linkJobActivity(userId, jobId, null, jdId, null);
    }

    @Test
    void aPastedJdWithNoJobLinksNothing() {
        // The paste-only path has no job, so there is no tracker row to point at the analysis.
        when(ai.analyzeJd("raw jd", userId)).thenReturn(new HashMap<>(Map.of("parsed", Map.of())));
        when(jds.save(any(JobJd.class))).thenAnswer(i -> i.getArgument(0));

        service.analyzeJd(userId, "raw jd", null);

        verifyNoInteractions(applicationService);
    }

    @Test
    void aJobTheUserCannotSeeIsStillRefusedBeforeAnythingIsLinked() {
        UUID missing = UUID.randomUUID();
        when(jobs.findById(missing)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.tailor(userId, missing, UUID.randomUUID()))
                .hasMessageContaining("Job not found");

        verify(applicationService, never())
                .linkJobActivity(any(), any(), any(), any(), any());
    }

    /** The match path defaults the resume to the current version; the link is that resolved id. */
    @Test
    void aMatchWithNoResumeNamedLinksTheCurrentVersionItFellBackTo() {
        UUID current = UUID.randomUUID();
        ResumeService resumes = mock(ResumeService.class);
        service = new JobService(jobs, mock(CompanyRepository.class), jds,
                mock(SavedJobRepository.class), mock(JobMatchRepository.class),
                mock(JobSearchRepository.class), resumes, applicationService, ai,
                mock(QueryEmbeddingService.class), TestTransactions.executing());
        when(resumes.currentResumeWithVersion(userId))
                .thenReturn(Optional.of(currentResume(current)));
        when(ai.matchJob(eq(jobId), eq(current), eq(userId)))
                .thenReturn(new HashMap<>(Map.of("match", Map.of())));

        service.match(userId, jobId, null);

        verify(applicationService).linkJobActivity(userId, jobId, current, null, null);
    }

    private static Resume currentResume(UUID versionId) {
        Resume resume = new Resume();
        resume.setCurrentVersionId(versionId);
        return resume;
    }
}
