package com.careeros.resume.web;

import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import com.careeros.common.PageDTO;
import com.careeros.resume.dto.ResumeDtos.CreateResumeRequest;
import com.careeros.resume.dto.ResumeDtos.ParseResumeResponse;
import com.careeros.resume.dto.ResumeDtos.ResumeDetail;
import com.careeros.resume.dto.ResumeDtos.ResumeListItem;
import com.careeros.resume.dto.ResumeDtos.ResumeVersionItem;
import com.careeros.resume.dto.ResumeDtos.SetCurrentVersionRequest;
import com.careeros.resume.dto.ResumeDtos.UpdateResumeRequest;
import com.careeros.resume.dto.ResumeDtos.UploadResumeResponse;
import com.careeros.resume.service.ResumeService;
import jakarta.validation.Valid;
import java.util.List;
import java.util.UUID;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api/v1/resumes")
public class ResumeController {

    private final ResumeService resumes;

    public ResumeController(ResumeService resumes) {
        this.resumes = resumes;
    }

    @GetMapping
    public PageDTO<ResumeListItem> list(@CurrentUser AuthUser user,
                                        @RequestParam(defaultValue = "0") int page,
                                        @RequestParam(defaultValue = "20") int size) {
        return resumes.list(user.id(), PageRequest.of(page, Math.min(size, 100)));
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ResumeListItem create(@CurrentUser AuthUser user,
                                 @RequestBody @Valid CreateResumeRequest request) {
        return resumes.create(user.id(), request);
    }

    @PostMapping("/upload")
    @ResponseStatus(HttpStatus.CREATED)
    public UploadResumeResponse upload(@CurrentUser AuthUser user,
                                       @RequestParam("file") MultipartFile file) {
        return resumes.upload(user.id(), file);
    }

    @GetMapping("/{id}")
    public ResumeDetail detail(@CurrentUser AuthUser user, @PathVariable UUID id) {
        return resumes.detail(user.id(), id);
    }

    @PatchMapping("/{id}")
    public ResumeListItem update(@CurrentUser AuthUser user, @PathVariable UUID id,
                                 @RequestBody @Valid UpdateResumeRequest request) {
        return resumes.update(user.id(), id, request);
    }

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void delete(@CurrentUser AuthUser user, @PathVariable UUID id) {
        resumes.delete(user.id(), id);
    }

    @PostMapping("/{id}/parse")
    public ParseResumeResponse parse(@CurrentUser AuthUser user, @PathVariable UUID id) {
        return resumes.parse(user.id(), id);
    }

    @PostMapping("/{id}/set-current")
    public ResumeListItem setCurrent(@CurrentUser AuthUser user, @PathVariable UUID id,
                                     @RequestBody @Valid SetCurrentVersionRequest request) {
        return resumes.setVersionCurrent(user.id(), id, request.versionId());
    }

    @GetMapping("/{id}/versions")
    public List<ResumeVersionItem> versions(@CurrentUser AuthUser user, @PathVariable UUID id) {
        return resumes.listVersions(user.id(), id);
    }
}
