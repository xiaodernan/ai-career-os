package com.careeros.application.service;

import com.careeros.application.dto.ApplicationDtos.ApplicationPacket;
import com.careeros.application.dto.ApplicationDtos.PacketJd;
import com.careeros.application.dto.ApplicationDtos.PacketMatch;
import com.careeros.application.dto.ApplicationDtos.PacketResume;
import com.careeros.application.entity.Application;
import com.careeros.application.repository.ApplicationLetterRepository;
import com.careeros.common.Json;
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
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Resolves the artifacts an application points at.
 *
 * <p>The application row stores three ids and nothing else about the material the reader sent.
 * The dialog could only print those ids, which is not a packet a reader can check: a uuid does
 * not say which resume version it is, whether it was tailored, what the JD asked for, or how the
 * match scored. This service reads the same user-scoped repositories that own those rows and
 * returns labels the dialog can show and link.
 *
 * <p>Every lookup is user-scoped even though the application already belongs to the caller: the
 * three link columns are accepted at create time, so a row can point at an id from another
 * account. A lookup that finds nothing is reported as an unavailable asset, never as that other
 * account's title.
 */
@Service
public class ApplicationPacketService {

    private final ApplicationService applications;
    private final ResumeVersionRepository resumeVersions;
    private final ResumeRepository resumes;
    private final JobJdRepository jds;
    private final JobMatchRepository matches;
    private final JobRepository jobs;
    private final CompanyRepository companies;
    private final ApplicationLetterRepository letters;
    private final InterviewSessionRepository interviews;
    private final InterviewEvaluationRepository evaluations;

    public ApplicationPacketService(ApplicationService applications,
                                    ResumeVersionRepository resumeVersions,
                                    ResumeRepository resumes,
                                    JobJdRepository jds,
                                    JobMatchRepository matches,
                                    JobRepository jobs,
                                    CompanyRepository companies,
                                    ApplicationLetterRepository letters,
                                    InterviewSessionRepository interviews,
                                    InterviewEvaluationRepository evaluations) {
        this.applications = applications;
        this.resumeVersions = resumeVersions;
        this.resumes = resumes;
        this.jds = jds;
        this.matches = matches;
        this.jobs = jobs;
        this.companies = companies;
        this.letters = letters;
        this.interviews = interviews;
        this.evaluations = evaluations;
    }

    @Transactional(readOnly = true)
    public ApplicationPacket packet(UUID userId, UUID applicationId) {
        Application app = applications.require(userId, applicationId);
        UUID resumeVersionId = app.getResumeVersionId();
        UUID jdId = app.getJdId();
        UUID matchId = app.getMatchId();
        int rehearsals = (int) interviews.countByApplicationIdAndUserId(app.getId(), userId);
        return new ApplicationPacket(
                app.getId(),
                resumeVersionId != null, resume(userId, resumeVersionId),
                jdId != null, jd(userId, jdId),
                matchId != null, match(userId, matchId),
                // A letter is not a link: there can be none, one, or several, and the card that
                // carries them is this application. The count is scoped to the caller like the
                // three lookups above, so a stray row can never be reported as this card's.
                (int) letters.countByApplicationIdAndUserId(app.getId(), userId),
                // 57.2: the practice the reader has done for this card. Scoped the
                // same way, so a rehearsal of somebody else's card is not counted.
                rehearsals,
                // 59.2: and how it went. No rehearsal means no read at all; a rehearsal
                // that never finished has no row to fold, so it simply contributes nothing.
                rehearsals == 0 ? null : bestRehearsalScore(userId, app.getId()));
    }

    /**
     * 59.2: the packet's rehearsal row says how the practice went, not only how often. The
     * evaluator's verdict is a key in the summary jsonb rather than a column, so the fold
     * happens here; the result stays on the same 0..1 scale the evaluation is stored in.
     */
    private Float bestRehearsalScore(UUID userId, UUID applicationId) {
        Float best = null;
        for (InterviewEvaluation evaluation : evaluations.findForApplication(userId, applicationId)) {
            Double overall = Json.dbl(evaluation.getSummary(), "overall");
            if (overall != null && (best == null || overall > best)) {
                best = overall.floatValue();
            }
        }
        return best;
    }

    private PacketResume resume(UUID userId, UUID versionId) {
        if (versionId == null) {
            return null;
        }
        return resumeVersions.findByIdAndUserId(versionId, userId)
                .map(version -> new PacketResume(
                        version.getId(), version.getResumeId(),
                        resumeTitle(userId, version),
                        version.getLabel(), version.getKind(), version.getCreatedAt()))
                .orElse(null);
    }

    private String resumeTitle(UUID userId, ResumeVersion version) {
        if (version.getResumeId() == null) {
            return null;
        }
        return resumes.findByIdAndUserId(version.getResumeId(), userId)
                .map(Resume::getTitle)
                .orElse(null);
    }

    private PacketJd jd(UUID userId, UUID jdId) {
        if (jdId == null) {
            return null;
        }
        return jds.findByIdAndUserId(jdId, userId)
                .map(analysis -> {
                    Job job = analysis.getJobId() == null ? null
                            : jobs.findById(analysis.getJobId()).orElse(null);
                    Map<String, Object> parsed = Json.obj(analysis.getParsed());
                    String title = Json.strOr(parsed, "title",
                            job == null ? null : job.getTitle());
                    String companyName = Json.strOr(parsed, "company",
                            companyName(job));
                    return new PacketJd(analysis.getId(), analysis.getJobId(),
                            title, companyName, analysis.getCreatedAt());
                })
                .orElse(null);
    }

    private String companyName(Job job) {
        if (job == null || job.getCompanyId() == null) {
            return null;
        }
        return companies.findById(job.getCompanyId()).map(Company::getName).orElse(null);
    }

    private PacketMatch match(UUID userId, UUID matchId) {
        if (matchId == null) {
            return null;
        }
        return matches.findByIdAndUserId(matchId, userId)
                .map(found -> new PacketMatch(found.getId(), found.getJobId(), found.getOverall(),
                        found.getCreatedAt()))
                .orElse(null);
    }
}
