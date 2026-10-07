package com.careeros.job.web;

import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import com.careeros.common.PageDTO;
import com.careeros.job.dto.JobDtos.CompanyDetail;
import com.careeros.job.dto.JobDtos.CompanyItem;
import com.careeros.job.service.JobService;
import java.util.UUID;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * Read-only on purpose. A company row is shared-catalog data: the application maintains it through
 * the job flow's upsert (creating or importing a job with an inline company), so no client-facing
 * write endpoint exists here. A previous PUT/DELETE pair was removed — DELETE cascaded through
 * jobs into every user's applications, and PUT updated by body name rather than by the path id.
 */
@RestController
@RequestMapping("/api/v1/companies")
public class CompanyController {

    private final JobService jobs;

    public CompanyController(JobService jobs) {
        this.jobs = jobs;
    }

    @GetMapping
    public PageDTO<CompanyItem> list(@RequestParam(required = false) String q,
                                     @RequestParam(defaultValue = "0") int page,
                                     @RequestParam(defaultValue = "20") int size) {
        return jobs.listCompanies(q, page, size);
    }

    /**
     * The company page reads through here. It takes the caller because the roles it answers with are
     * the board's own rows, and every one of those carries that caller's latest cached match — a
     * company profile is the same to everyone, the ordering beside it is not.
     */
    @GetMapping("/{id}")
    public CompanyDetail get(@CurrentUser AuthUser user, @PathVariable UUID id) {
        return jobs.companyDetail(user.id(), id);
    }
}
