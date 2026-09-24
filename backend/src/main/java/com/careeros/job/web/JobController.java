package com.careeros.job.web;

import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import com.careeros.common.PageDTO;
import com.careeros.job.dto.JobDtos.CoverLetterRequest;
import com.careeros.job.dto.JobDtos.CreateJobRequest;
import com.careeros.job.dto.JobDtos.ImportJobRequest;
import com.careeros.job.dto.JobDtos.JobDetail;
import com.careeros.job.dto.JobDtos.JobListItem;
import com.careeros.job.dto.JobDtos.MatchRequest;
import com.careeros.job.dto.JobDtos.MatchResponse;
import com.careeros.job.dto.JobDtos.SaveJobRequest;
import com.careeros.job.dto.JobDtos.SavedJobItem;
import com.careeros.job.dto.JobDtos.TailorRequest;
import com.careeros.job.service.JobService;
import com.careeros.resume.dto.ResumeDtos.ResumeVersionItem;
import com.careeros.resume.dto.ResumeDtos.TailoredVersionRequest;
import jakarta.validation.Valid;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/jobs")
public class JobController {

    private final JobService jobs;

    public JobController(JobService jobs) {
        this.jobs = jobs;
    }

    @GetMapping
    public PageDTO<JobListItem> list(@CurrentUser AuthUser user,
                                     @RequestParam(required = false) String q,
                                     @RequestParam(required = false) List<String> skills,
                                     @RequestParam(required = false) String location,
                                     @RequestParam(required = false) String remote,
                                     @RequestParam(required = false) String company,
                                     @RequestParam(name = "minSalary", required = false) Integer minSalary,
                                     @RequestParam(name = "maxSalary", required = false) Integer maxSalary,
                                     @RequestParam(required = false) String status,
                                     @RequestParam(defaultValue = "posted") String sort,
                                     @RequestParam(defaultValue = "0") int page,
                                     @RequestParam(defaultValue = "20") int size) {
        return jobs.list(user.id(), q, skills, location, remote, company, minSalary, maxSalary,
                status, sort, page, size);
    }

    @GetMapping("/saved")
    public List<SavedJobItem> saved(@CurrentUser AuthUser user) {
        return jobs.saved(user.id());
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public JobListItem create(@CurrentUser AuthUser user, @RequestBody @Valid CreateJobRequest request) {
        return jobs.create(user.id(), request);
    }

    @PostMapping("/import")
    @ResponseStatus(HttpStatus.CREATED)
    public JobListItem importJob(@CurrentUser AuthUser user,
                                 @RequestBody @Valid ImportJobRequest request) {
        return jobs.importJob(user.id(), request);
    }

    @GetMapping("/{id}")
    public JobDetail detail(@CurrentUser AuthUser user, @PathVariable UUID id) {
        return jobs.detail(user.id(), id);
    }

    @PostMapping("/{id}/save")
    public void save(@CurrentUser AuthUser user, @PathVariable UUID id,
                     @RequestBody(required = false) SaveJobRequest request) {
        jobs.saveJob(user.id(), id, request == null ? null : request.note());
    }

    @DeleteMapping("/{id}/save")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void unsave(@CurrentUser AuthUser user, @PathVariable UUID id) {
        jobs.unsaveJob(user.id(), id);
    }

    @PostMapping("/{id}/match")
    public MatchResponse match(@CurrentUser AuthUser user, @PathVariable UUID id,
                               @RequestBody(required = false) MatchRequest request) {
        return jobs.match(user.id(), id, request == null ? null : request.resumeVersionId());
    }

    @PostMapping("/{id}/tailor")
    public Map<String, Object> tailor(@CurrentUser AuthUser user, @PathVariable UUID id,
                                      @RequestBody(required = false) TailorRequest request) {
        return jobs.tailor(user.id(), id, request == null ? null : request.resumeVersionId());
    }

    /** Keeps the draft the previous /tailor call produced as a new resume version. */
    @PostMapping("/{id}/tailored-version")
    @ResponseStatus(HttpStatus.CREATED)
    public ResumeVersionItem saveTailored(@CurrentUser AuthUser user, @PathVariable UUID id,
                                         @RequestBody TailoredVersionRequest request) {
        return jobs.saveTailored(user.id(), id, request);
    }

    @PostMapping("/{id}/cover-letter")
    public Map<String, Object> coverLetter(@CurrentUser AuthUser user, @PathVariable UUID id,
                                           @RequestBody(required = false) CoverLetterRequest request) {
        return jobs.coverLetter(user.id(), id,
                request == null ? null : request.resumeVersionId(),
                request == null ? null : request.mode(),
                request == null ? null : request.previous(),
                request == null ? null : request.goal(),
                request == null ? null : request.tone(),
                request == null ? null : request.length());
    }
}
