package com.careeros.job.web;

import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import com.careeros.common.PageDTO;
import com.careeros.job.dto.JobDtos.CompanyDetail;
import com.careeros.job.dto.JobDtos.CompanyItem;
import com.careeros.job.dto.JobDtos.CompanyRequest;
import com.careeros.job.service.JobService;
import jakarta.validation.Valid;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

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

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public CompanyItem create(@RequestBody @Valid CompanyRequest request) {
        return jobs.upsertCompany(request);
    }

    @PutMapping("/{id}")
    public CompanyItem update(@PathVariable UUID id, @RequestBody @Valid CompanyRequest request) {
        jobs.getCompany(id); // existence guard
        return jobs.upsertCompany(request);
    }

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void delete(@PathVariable UUID id) {
        jobs.deleteCompany(id);
    }
}
