package com.careeros.job.service;

import com.careeros.ai.AiServiceClient;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.common.Json;
import com.careeros.common.PageDTO;
import com.careeros.job.dto.JobDtos.CompanyItem;
import com.careeros.job.dto.JobDtos.CompanyRequest;
import com.careeros.job.dto.JobDtos.CreateJobRequest;
import com.careeros.job.dto.JobDtos.ImportJobRequest;
import com.careeros.job.dto.JobDtos.JdItem;
import com.careeros.job.dto.JobDtos.JobDetail;
import com.careeros.job.dto.JobDtos.JobListItem;
import com.careeros.job.dto.JobDtos.MatchResponse;
import com.careeros.job.dto.JobDtos.MatchSummary;
import com.careeros.job.dto.JobDtos.SavedJobItem;
import com.careeros.job.entity.Company;
import com.careeros.job.entity.Job;
import com.careeros.job.entity.JobJd;
import com.careeros.job.entity.JobMatch;
import com.careeros.job.entity.SavedJob;
import com.careeros.job.repository.CompanyRepository;
import com.careeros.job.repository.JobJdRepository;
import com.careeros.job.repository.JobMatchRepository;
import com.careeros.job.repository.JobRepository;
import com.careeros.job.repository.JobSearchRepository;
import com.careeros.job.repository.SavedJobRepository;
import com.careeros.resume.entity.Resume;
import com.careeros.resume.service.ResumeService;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Jobs, companies, saved jobs, JD import/analysis and AI match proxying. */
@Service
public class JobService {

    private final JobRepository jobs;
    private final CompanyRepository companies;
    private final JobJdRepository jds;
    private final SavedJobRepository savedJobs;
    private final JobMatchRepository matches;
    private final JobSearchRepository search;
    private final ResumeService resumeService;
    private final AiServiceClient ai;

    public JobService(JobRepository jobs, CompanyRepository companies, JobJdRepository jds,
                      SavedJobRepository savedJobs, JobMatchRepository matches,
                      JobSearchRepository search, ResumeService resumeService, AiServiceClient ai) {
        this.jobs = jobs;
        this.companies = companies;
        this.jds = jds;
        this.savedJobs = savedJobs;
        this.matches = matches;
        this.search = search;
        this.resumeService = resumeService;
        this.ai = ai;
    }

    @Transactional(readOnly = true)
    public PageDTO<JobListItem> list(UUID userId, String q, List<String> skills, String location,
                                     String remote, String company, Integer minSalary,
                                     Integer maxSalary, String status, String sort,
                                     int page, int size) {
        var filters = new JobSearchRepository.Filters(userId, q, skills, location, remote, company,
                minSalary, maxSalary, status, sort, page, size);
        List<JobListItem> items = search.search(filters);
        return PageDTO.of(items, search.count(filters), page, size);
    }

    @Transactional(readOnly = true)
    public JobDetail detail(UUID userId, UUID jobId) {
        Job job = requireJob(jobId);
        Company company = companies.findById(job.getCompanyId()).orElse(null);
        JobListItem item = toItem(job, company == null ? "" : company.getName());
        MatchSummary match = matches.findFirstByUserIdAndJobIdOrderByCreatedAtDesc(userId, jobId)
                .map(JobService::toSummary).orElse(null);
        JdItem jd = jds.findFirstByJobIdAndUserIdOrderByCreatedAtDesc(jobId, userId)
                .map(JobService::toJdItem).orElse(null);
        String jdText = jd == null ? null : jd.rawText();
        return new JobDetail(item.id(), item.title(), item.companyId(),
                company == null ? null : toCompanyItem(company,
                        companies.countOpenRoles(company.getId())),
                item.location(), item.remoteType(), item.employmentType(), item.salaryMin(),
                item.salaryMax(), item.salaryCurrency(), item.experienceYears(), job.getDescription(),
                job.getRequirements(), job.getNiceToHave(), job.getResponsibilities(), job.getSkills(),
                job.getStatus(), job.getSource(), job.getExternalUrl(), job.getPostedAt(),
                match, jd == null ? null : new JdItem(jd.id(), jd.jobId(), jdText, jd.parsed(),
                        jd.createdAt()),
                savedJobs.existsByUserIdAndJobId(userId, jobId));
    }

    @Transactional
    public JobListItem create(UUID userId, CreateJobRequest request) {
        UUID companyId = request.companyId();
        if (companyId == null) {
            CompanyRequest cr = request.company();
            if (cr == null || cr.name() == null || cr.name().isBlank()) {
                throw new ApiException(ApiErrorCode.VALIDATION_FAILED,
                        "company_id or company.name is required");
            }
            companyId = upsertCompany(cr).id();
        } else if (!companies.existsById(companyId)) {
            throw new ApiException(ApiErrorCode.COMPANY_NOT_FOUND, "Company not found");
        }
        Job job = buildJob(request.title(), companyId, request.location(), request.remoteType(),
                request.employmentType(), request.salaryMin(), request.salaryMax(),
                request.salaryCurrency(), request.experienceYears(), request.description(),
                request.requirements(), request.niceToHave(), request.responsibilities(),
                request.skills(), request.status(), request.externalUrl(), "user_paste");
        Company company = companies.findById(companyId).orElseThrow();
        return toItem(job, company.getName());
    }

    public JobListItem importJob(UUID userId, ImportJobRequest request) {
        Map<String, Object> result = ai.analyzeJd(request.rawText(), userId);
        return persistImport(userId, request, result);
    }

    @Transactional
    public JobListItem persistImport(UUID userId, ImportJobRequest request, Map<String, Object> result) {
        Map<String, Object> parsed = Json.obj(result.get("parsed"));
        String title = Json.strOr(parsed, "title", "Imported job");
        String companyName = Json.strOr(parsed, "company", "Unknown company");
        Company company = companies.findByName(companyName).orElseGet(() -> {
            Company c = new Company();
            c.setName(companyName);
            c.setSources(List.of(Map.of("type", "user_paste")));
            return companies.save(c);
        });
        List<String> skills = java.util.stream.Stream
                .concat(Json.arr(parsed.get("requiredSkills")).stream()
                                .map(o -> Json.str(Json.obj(o), "name")),
                        Json.arr(parsed.get("preferredSkills")).stream()
                                .map(o -> Json.str(Json.obj(o), "name")))
                .filter(s -> s != null && !s.isBlank()).distinct().toList();
        Job job = buildJob(title, company.getId(), Json.str(parsed, "location"), null, null,
                null, null, null, Json.integer(parsed, "experienceYears"), request.rawText(),
                List.of(), List.of(), Json.strList(parsed.get("responsibilities")), skills,
                null, null, "user_paste");
        JobJd jd = new JobJd();
        jd.setJobId(job.getId());
        jd.setUserId(userId);
        jd.setRawText(request.rawText());
        jd.setParsed(parsed);
        jds.save(jd);
        return toItem(job, company.getName());
    }

    public MatchResponse match(UUID userId, UUID jobId, UUID resumeVersionId) {
        requireJob(jobId);
        UUID rvId = resumeVersionId;
        if (rvId == null) {
            Resume resume = resumeService.currentResumeWithVersion(userId)
                    .orElseThrow(() -> new ApiException(ApiErrorCode.RESUME_NOT_FOUND,
                            "No parsed resume available for matching"));
            rvId = resume.getCurrentVersionId();
        }
        Map<String, Object> result = ai.matchJob(jobId, rvId, userId);
        Map<String, Object> match = Json.obj(result.get("match"));
        UUID matchId = Json.uuidOrNull(result, "match_id");
        return new MatchResponse(match, matchId, Json.obj(result.get("jd")));
    }

    @Transactional(readOnly = true)
    public List<SavedJobItem> saved(UUID userId) {
        return savedJobs.findByUserIdOrderByCreatedAtDesc(userId).stream()
                .map(s -> jobs.findById(s.getJobId()).map(job -> {
                    String name = companies.findById(job.getCompanyId())
                            .map(Company::getName).orElse("");
                    return new SavedJobItem(toItem(job, name), s.getNote(), s.getCreatedAt());
                }).orElse(null))
                .filter(java.util.Objects::nonNull)
                .toList();
    }

    @Transactional
    public void saveJob(UUID userId, UUID jobId, String note) {
        requireJob(jobId);
        if (savedJobs.existsByUserIdAndJobId(userId, jobId)) {
            return;
        }
        SavedJob s = new SavedJob();
        s.setUserId(userId);
        s.setJobId(jobId);
        s.setNote(note);
        savedJobs.save(s);
    }

    @Transactional
    public void unsaveJob(UUID userId, UUID jobId) {
        requireJob(jobId);
        savedJobs.deleteById(new SavedJob.SavedJobId(userId, jobId));
    }

    @Transactional
    public JobJd analyzeJd(UUID userId, String rawText, UUID jobId) {
        if (jobId != null) {
            requireJob(jobId);
        }
        Map<String, Object> result = ai.analyzeJd(rawText, userId);
        JobJd jd = new JobJd();
        jd.setUserId(userId);
        jd.setJobId(jobId);
        jd.setRawText(rawText);
        jd.setParsed(Json.obj(result.get("parsed")));
        return jds.save(jd);
    }

    @Transactional(readOnly = true)
    public JobJd requireJd(UUID userId, UUID jdId) {
        return jds.findByIdAndUserId(jdId, userId)
                .orElseThrow(() -> new ApiException(ApiErrorCode.JD_NOT_FOUND, "Job JD not found"));
    }

    public Map<String, Object> jdSuggestions(UUID userId, UUID resumeVersionId, String jdRaw) {
        return ai.jdSuggestions(resumeVersionId, jdRaw, userId);
    }

    public Map<String, Object> tailor(UUID userId, UUID jobId, UUID resumeVersionId) {
        requireJob(jobId);
        UUID rvId = resumeVersionId;
        if (rvId == null) {
            rvId = resumeService.currentResumeWithVersion(userId)
                    .orElseThrow(() -> new ApiException(ApiErrorCode.RESUME_NOT_FOUND,
                            "No resume available for tailoring"))
                    .getCurrentVersionId();
        }
        return ai.tailorResume(jobId, rvId, userId);
    }

    public Map<String, Object> coverLetter(UUID userId, UUID jobId, UUID resumeVersionId,
                                           String mode, String previous, String goal) {
        requireJob(jobId);
        UUID rvId = resumeVersionId;
        if (rvId == null) {
            rvId = resumeService.currentResumeWithVersion(userId)
                    .orElseThrow(() -> new ApiException(ApiErrorCode.RESUME_NOT_FOUND,
                            "No resume available"))
                    .getCurrentVersionId();
        }
        return ai.coverLetter(jobId, rvId, mode, previous, goal, userId);
    }

    @Transactional
    public CompanyItem upsertCompany(CompanyRequest request) {
        Company company = companies.findByName(request.name().trim()).orElseGet(Company::new);
        if (request.website() != null) {
            company.setWebsite(request.website());
        }
        if (request.logoUrl() != null) {
            company.setLogoUrl(request.logoUrl());
        }
        if (request.industry() != null) {
            company.setIndustry(request.industry());
        }
        if (request.size() != null) {
            company.setSize(request.size());
        }
        if (request.overview() != null) {
            company.setOverview(request.overview());
        }
        if (request.techStack() != null) {
            company.setTechStack(request.techStack());
        }
        if (request.culture() != null) {
            company.setCulture(request.culture());
        }
        if (request.interviewProcess() != null) {
            company.setInterviewProcess(request.interviewProcess());
        }
        if (request.sources() != null && !request.sources().isEmpty()) {
            company.setSources(request.sources());
        }
        companies.save(company);
        return toCompanyItem(company, companies.countOpenRoles(company.getId()));
    }

    @Transactional(readOnly = true)
    public PageDTO<CompanyItem> listCompanies(String q, int page, int size) {
        var pageable = PageRequest.of(page, size);
        var result = (q == null || q.isBlank())
                ? companies.findAll(pageable)
                : companies.findByNameContainingIgnoreCase(q, pageable);
        Map<UUID, Long> counts = new java.util.HashMap<>();
        for (Object[] row : companies.openRoleCounts()) {
            counts.put((UUID) row[0], ((Number) row[1]).longValue());
        }
        return PageDTO.from(result, c -> toCompanyItem(c, counts.getOrDefault(c.getId(), 0L)));
    }

    @Transactional(readOnly = true)
    public CompanyItem getCompany(UUID id) {
        Company c = companies.findById(id)
                .orElseThrow(() -> new ApiException(ApiErrorCode.COMPANY_NOT_FOUND, "Company not found"));
        return toCompanyItem(c, companies.countOpenRoles(id));
    }

    @Transactional
    public void deleteCompany(UUID id) {
        Company c = companies.findById(id)
                .orElseThrow(() -> new ApiException(ApiErrorCode.COMPANY_NOT_FOUND, "Company not found"));
        companies.delete(c); // jobs cascade with the company per schema
    }

    public Job requireJob(UUID jobId) {
        return jobs.findById(jobId)
                .orElseThrow(() -> new ApiException(ApiErrorCode.JOB_NOT_FOUND, "Job not found"));
    }

    private Job buildJob(String title, UUID companyId, String location, String remoteType,
                         String employmentType, Integer salaryMin, Integer salaryMax,
                         String salaryCurrency, Integer experienceYears, String description,
                         List<String> requirements, List<String> niceToHave,
                         List<String> responsibilities, List<String> skills, String status,
                         String externalUrl, String source) {
        Job job = new Job();
        job.setTitle(title);
        job.setCompanyId(companyId);
        job.setLocation(location);
        if (remoteType != null) {
            job.setRemoteType(remoteType);
        }
        if (employmentType != null) {
            job.setEmploymentType(employmentType);
        }
        job.setSalaryMin(salaryMin);
        job.setSalaryMax(salaryMax);
        if (salaryCurrency != null) {
            job.setSalaryCurrency(salaryCurrency);
        }
        job.setExperienceYears(experienceYears);
        job.setDescription(description);
        job.setRequirements(requirements);
        job.setNiceToHave(niceToHave);
        job.setResponsibilities(responsibilities);
        job.setSkills(skills);
        if (status != null) {
            job.setStatus(status);
        }
        job.setExternalUrl(externalUrl);
        job.setSource(source);
        return jobs.save(job);
    }

    static JobListItem toItem(Job job, String companyName) {
        return toItemInternal(job, companyName);
    }

    static MatchSummary toSummary(JobMatch m) {
        return new MatchSummary(m.getId(), m.getOverall(), m.getTechnical(), m.getExperience(),
                m.getProjects(), m.getEducation(), m.getMatchedSkills(), m.getMissingSkills(),
                m.getEvidence(), m.getNarrative(), m.getCreatedAt());
    }

    public static JdItem toJdItem(JobJd jd) {
        return new JdItem(jd.getId(), jd.getJobId(), jd.getRawText(), jd.getParsed(), jd.getCreatedAt());
    }

    private static JobListItem toItemInternal(Job job, String companyName) {
        return new JobListItem(job.getId(), job.getTitle(), job.getCompanyId(), companyName,
                job.getLocation(), job.getRemoteType(), job.getEmploymentType(), job.getSalaryMin(),
                job.getSalaryMax(), job.getSalaryCurrency(), job.getExperienceYears(),
                job.getStatus(), job.getSource(), job.getExternalUrl(), job.getPostedAt(),
                job.getSkills(), null, null);
    }

    private static CompanyItem toCompanyItem(Company c, long openRoles) {
        return new CompanyItem(c.getId(), c.getName(), c.getWebsite(), c.getLogoUrl(),
                c.getIndustry(), c.getSize(), c.getOverview(), c.getTechStack(), openRoles);
    }

    public Optional<JobMatch> latestMatch(UUID userId, UUID jobId) {
        return matches.findFirstByUserIdAndJobIdOrderByCreatedAtDesc(userId, jobId);
    }
}
