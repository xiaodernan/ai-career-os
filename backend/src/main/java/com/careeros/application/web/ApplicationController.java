package com.careeros.application.web;

import com.careeros.application.dto.ApplicationDtos.ApplicationItem;
import com.careeros.application.dto.ApplicationDtos.ApplicationPacket;
import com.careeros.application.dto.ApplicationDtos.CreateApplicationRequest;
import com.careeros.application.dto.ApplicationDtos.LetterItem;
import com.careeros.application.dto.ApplicationDtos.ReorderRequest;
import com.careeros.application.dto.ApplicationDtos.SaveLetterRequest;
import com.careeros.application.dto.ApplicationDtos.TimelineEvent;
import com.careeros.application.dto.ApplicationDtos.UpdateApplicationRequest;
import com.careeros.application.dto.ApplicationDtos.UpdateLetterRequest;
import com.careeros.application.service.ApplicationLetterService;
import com.careeros.application.service.ApplicationService;
import com.careeros.application.service.ApplicationPacketService;
import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import com.careeros.common.PageDTO;
import com.careeros.common.Paging;
import jakarta.validation.Valid;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/applications")
public class ApplicationController {

    private final ApplicationService applications;
    private final ApplicationPacketService packets;
    private final ApplicationLetterService letters;

    public ApplicationController(ApplicationService applications, ApplicationPacketService packets,
                                 ApplicationLetterService letters) {
        this.applications = applications;
        this.packets = packets;
        this.letters = letters;
    }

    @GetMapping
    public PageDTO<ApplicationItem> list(@CurrentUser AuthUser user,
                                         @RequestParam(required = false) String status,
                                         @RequestParam(required = false) UUID jobId,
                                         @RequestParam(defaultValue = "0") int page,
                                         @RequestParam(defaultValue = "50") int size) {
        return applications.list(user.id(), status, jobId, Paging.of(page, size).pageable());
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ApplicationItem create(@CurrentUser AuthUser user,
                                  @RequestBody @Valid CreateApplicationRequest request) {
        return applications.create(user.id(), request);
    }

    @GetMapping("/{id}")
    public ApplicationItem get(@CurrentUser AuthUser user, @PathVariable UUID id) {
        return ApplicationService.toItem(applications.require(user.id(), id));
    }

    @PatchMapping("/{id}")
    public ApplicationItem patch(@CurrentUser AuthUser user, @PathVariable UUID id,
                                 @RequestBody @Valid UpdateApplicationRequest request) {
        return applications.update(user.id(), id, request);
    }

    @PutMapping("/{id}/reorder")
    public ApplicationItem reorder(@CurrentUser AuthUser user, @PathVariable UUID id,
                                   @RequestBody @Valid ReorderRequest request) {
        return applications.reorder(user.id(), id, request);
    }

    @GetMapping("/{id}/timeline")
    public List<TimelineEvent> timeline(@CurrentUser AuthUser user, @PathVariable UUID id) {
        return applications.timeline(user.id(), id);
    }

    @GetMapping("/{id}/packet")
    public ApplicationPacket packet(@CurrentUser AuthUser user, @PathVariable UUID id) {
        return packets.packet(user.id(), id);
    }

    @GetMapping("/{id}/letters")
    public List<LetterItem> letters(@CurrentUser AuthUser user, @PathVariable UUID id) {
        return letters.list(user.id(), id);
    }

    @PostMapping("/{id}/letters")
    @ResponseStatus(HttpStatus.CREATED)
    public LetterItem saveLetter(@CurrentUser AuthUser user, @PathVariable UUID id,
                                 @RequestBody @Valid SaveLetterRequest request) {
        return letters.save(user.id(), id, request);
    }

    @DeleteMapping("/{id}/letters/{letterId}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void deleteLetter(@CurrentUser AuthUser user, @PathVariable UUID id,
                             @PathVariable UUID letterId) {
        letters.delete(user.id(), id, letterId);
    }

    @PatchMapping("/{id}/letters/{letterId}")
    public LetterItem updateLetter(@CurrentUser AuthUser user, @PathVariable UUID id,
                                   @PathVariable UUID letterId,
                                   @RequestBody @Valid UpdateLetterRequest request) {
        return letters.update(user.id(), id, letterId, request);
    }

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void delete(@CurrentUser AuthUser user, @PathVariable UUID id) {
        applications.delete(user.id(), id);
    }
}
