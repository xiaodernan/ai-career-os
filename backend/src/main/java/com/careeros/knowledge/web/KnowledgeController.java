package com.careeros.knowledge.web;

import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import com.careeros.common.PageDTO;
import com.careeros.knowledge.dto.KnowledgeDtos.DocumentStatus;
import com.careeros.knowledge.dto.KnowledgeDtos.IngestResultDto;
import com.careeros.knowledge.dto.KnowledgeDtos.NoteItem;
import com.careeros.knowledge.dto.KnowledgeDtos.NoteRequest;
import com.careeros.knowledge.dto.KnowledgeDtos.SourceItem;
import com.careeros.knowledge.dto.KnowledgeDtos.TextIngestRequest;
import com.careeros.knowledge.dto.KnowledgeDtos.TextIngestResponse;
import com.careeros.knowledge.service.KnowledgeService;
import jakarta.validation.Valid;
import java.util.UUID;
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
@RequestMapping("/api/v1/knowledge")
public class KnowledgeController {

    private final KnowledgeService knowledge;

    public KnowledgeController(KnowledgeService knowledge) {
        this.knowledge = knowledge;
    }

    @GetMapping("/sources")
    public PageDTO<SourceItem> sources(@CurrentUser AuthUser user,
                                       @RequestParam(defaultValue = "0") int page,
                                       @RequestParam(defaultValue = "20") int size) {
        return knowledge.listSources(user.id(), page, size);
    }

    @DeleteMapping("/sources/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void deleteSource(@CurrentUser AuthUser user, @PathVariable UUID id) {
        knowledge.deleteSource(user.id(), id);
    }

    @GetMapping("/sources/{id}/status")
    public DocumentStatus sourceStatus(@CurrentUser AuthUser user, @PathVariable UUID id) {
        return knowledge.sourceStatus(user.id(), id);
    }

    @GetMapping("/notes")
    public PageDTO<NoteItem> notes(@CurrentUser AuthUser user,
                                   @RequestParam(defaultValue = "0") int page,
                                   @RequestParam(defaultValue = "20") int size) {
        return knowledge.listNotes(user.id(), page, size);
    }

    @PostMapping("/notes")
    @ResponseStatus(HttpStatus.CREATED)
    public NoteItem createNote(@CurrentUser AuthUser user, @RequestBody @Valid NoteRequest request) {
        return knowledge.createNote(user.id(), request);
    }

    @PatchMapping("/notes/{id}")
    public NoteItem updateNote(@CurrentUser AuthUser user, @PathVariable UUID id,
                               @RequestBody @Valid NoteRequest request) {
        return knowledge.updateNote(user.id(), id, request);
    }

    @DeleteMapping("/notes/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void deleteNote(@CurrentUser AuthUser user, @PathVariable UUID id) {
        knowledge.deleteNote(user.id(), id);
    }

    @PostMapping("/text")
    public TextIngestResponse ingestText(@CurrentUser AuthUser user,
                                         @RequestBody @Valid TextIngestRequest request) {
        return knowledge.ingestText(user.id(), request.title(), request.text(), request.kind(),
                request.refId());
    }

    @PostMapping("/documents")
    @ResponseStatus(HttpStatus.CREATED)
    public IngestResultDto uploadDocument(@CurrentUser AuthUser user,
                                          @RequestParam("file") MultipartFile file,
                                          @RequestParam(required = false) String kind,
                                          @RequestParam(required = false) String title) {
        return knowledge.uploadDocument(user.id(), file, kind, title);
    }
}
