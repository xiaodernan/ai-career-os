package com.careeros.resume.web;

import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import com.careeros.resume.dto.ResumeDtos.ResumeVersionItem;
import com.careeros.resume.service.ResumeService;
import java.util.UUID;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/resume-versions")
public class ResumeVersionController {

    private final ResumeService resumes;

    public ResumeVersionController(ResumeService resumes) {
        this.resumes = resumes;
    }

    @GetMapping
    public java.util.List<ResumeVersionItem> list(@CurrentUser AuthUser user,
                                                  @RequestParam("resumeId") UUID resumeId) {
        return resumes.listVersions(user.id(), resumeId);
    }

    @GetMapping("/{id}")
    public ResumeVersionItem get(@CurrentUser AuthUser user, @PathVariable UUID id) {
        return resumes.versionMeta(user.id(), id);
    }
}
