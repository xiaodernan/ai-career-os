package com.careeros.resume.service;

import com.careeros.ai.AiServiceClient;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.common.Json;
import com.careeros.common.PageDTO;
import com.careeros.common.Paging;
import com.careeros.common.Texts;
import com.careeros.knowledge.entity.Document;
import com.careeros.knowledge.entity.KnowledgeSource;
import com.careeros.knowledge.repository.DocumentRepository;
import com.careeros.knowledge.repository.KnowledgeSourceRepository;
import com.careeros.knowledge.service.FileIngestService;
import com.careeros.knowledge.service.KnowledgeService;
import com.careeros.resume.dto.ResumeDtos.AchievementItem;
import com.careeros.resume.dto.ResumeDtos.CreateResumeRequest;
import com.careeros.resume.dto.ResumeDtos.EducationItem;
import com.careeros.resume.dto.ResumeDtos.ExperienceItem;
import com.careeros.resume.dto.ResumeDtos.ParseResumeResponse;
import com.careeros.resume.dto.ResumeDtos.ProjectItem;
import com.careeros.resume.dto.ResumeDtos.ResumeDetail;
import com.careeros.resume.dto.ResumeDtos.ResumeListItem;
import com.careeros.resume.dto.ResumeDtos.ResumeVersionItem;
import com.careeros.resume.dto.ResumeDtos.SkillItem;
import com.careeros.resume.dto.ResumeDtos.TailoredVersionRequest;
import com.careeros.resume.dto.ResumeDtos.UpdateResumeRequest;
import com.careeros.resume.dto.ResumeDtos.UploadResumeResponse;
import com.careeros.resume.entity.Achievement;
import com.careeros.resume.entity.Education;
import com.careeros.resume.entity.Experience;
import com.careeros.resume.entity.Project;
import com.careeros.resume.entity.Resume;
import com.careeros.resume.entity.ResumeSkill;
import com.careeros.resume.entity.ResumeVersion;
import com.careeros.resume.entity.Skill;
import com.careeros.resume.repository.AchievementRepository;
import com.careeros.resume.repository.EducationRepository;
import com.careeros.resume.repository.ExperienceRepository;
import com.careeros.resume.repository.ProjectRepository;
import com.careeros.resume.repository.ResumeRepository;
import com.careeros.resume.repository.ResumeSkillRepository;
import com.careeros.resume.repository.ResumeVersionRepository;
import com.careeros.resume.repository.SkillRepository;
import com.careeros.storage.FileValidator;
import com.careeros.storage.StorageService;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

/** Resume CRUD, upload, AI parse and structured child-table projection. */
@Service
public class ResumeService {

    private final ResumeRepository resumes;
    private final ResumeVersionRepository versions;
    private final ExperienceRepository experiences;
    private final ProjectRepository projects;
    private final EducationRepository educations;
    private final AchievementRepository achievements;
    private final SkillRepository skills;
    private final ResumeSkillRepository resumeSkills;
    private final KnowledgeSourceRepository sources;
    private final DocumentRepository documents;
    private final KnowledgeService knowledge;
    private final FileIngestService fileIngest;
    private final StorageService storage;
    private final AiServiceClient ai;

    private static final Logger log = LoggerFactory.getLogger(ResumeService.class);

    public ResumeService(ResumeRepository resumes, ResumeVersionRepository versions,
                         ExperienceRepository experiences, ProjectRepository projects,
                         EducationRepository educations, AchievementRepository achievements,
                         SkillRepository skills, ResumeSkillRepository resumeSkills,
                         KnowledgeSourceRepository sources, KnowledgeService knowledge,
                         DocumentRepository documents, FileIngestService fileIngest,
                         StorageService storage, AiServiceClient ai) {
        this.resumes = resumes;
        this.versions = versions;
        this.experiences = experiences;
        this.projects = projects;
        this.educations = educations;
        this.achievements = achievements;
        this.skills = skills;
        this.resumeSkills = resumeSkills;
        this.sources = sources;
        this.documents = documents;
        this.knowledge = knowledge;
        this.fileIngest = fileIngest;
        this.storage = storage;
        this.ai = ai;
    }

    @Transactional(readOnly = true)
    public PageDTO<ResumeListItem> list(UUID userId, Pageable pageable) {
        var page = resumes.findByUserIdOrderByCreatedAtDescIdAsc(userId, pageable);
        return PageDTO.from(page, ResumeListItem::from);
    }

    @Transactional(readOnly = true)
    public ResumeDetail detail(UUID userId, UUID resumeId) {
        Resume resume = requireResume(userId, resumeId);
        ResumeVersion version = currentVersion(resume).orElse(null);
        if (version == null) {
            return new ResumeDetail(resume.getId(), resume.getTitle(), resume.getStatus(),
                    resume.getSourceFileKey(), resume.getCurrentVersionId(), resume.getCreatedAt(),
                    Map.of(), null, null, List.of(), List.of(), List.of(), List.of(), List.of());
        }
        return new ResumeDetail(resume.getId(), resume.getTitle(), resume.getStatus(),
                resume.getSourceFileKey(), resume.getCurrentVersionId(), resume.getCreatedAt(),
                version.getStructured(), version.getPlaintext(), version.getScore(),
                experiences.findByResumeVersionIdOrderByOrdinalAsc(version.getId()).stream()
                        .map(e -> new ExperienceItem(e.getId(), e.getCompany(), e.getTitle(),
                                e.getStartDate(),
                                e.getEndMonth() == null ? null : e.getEndMonth().toString(),
                                e.getLocation(), e.getBullets(), e.getSummary(), e.getOrdinal()))
                        .toList(),
                projects.findByResumeVersionIdOrderByOrdinalAsc(version.getId()).stream()
                        .map(p -> new ProjectItem(p.getId(), p.getName(), p.getRole(), p.getPeriod(),
                                p.getBullets(), p.getTech(), p.getUrl(), p.getOrdinal()))
                        .toList(),
                educations.findByResumeVersionIdOrderByOrdinalAsc(version.getId()).stream()
                        .map(ed -> new EducationItem(ed.getId(), ed.getSchool(), ed.getDegree(),
                                ed.getField(), ed.getStartYear(), ed.getEndYear(), ed.getGpa(),
                                ed.getCourses(), ed.getOrdinal()))
                        .toList(),
                achievements.findByResumeVersionIdOrderByOrdinalAsc(version.getId()).stream()
                        .map(a -> new AchievementItem(a.getId(), a.getText(), a.getOrdinal()))
                        .toList(),
                skillItems(version.getId()));
    }

    @Transactional(readOnly = true)
    public List<ResumeVersionItem> listVersions(UUID userId, UUID resumeId) {
        requireResume(userId, resumeId);
        return versions.findByResumeIdAndUserIdOrderByCreatedAtDesc(resumeId, userId).stream()
                .map(v -> new ResumeVersionItem(v.getId(), v.getResumeId(), v.getLabel(),
                        v.getKind(), v.getJobId(), v.getCreatedAt(), v.getDiff(), v.getScore()))
                .toList();
    }

    @Transactional(readOnly = true)
    public ResumeVersionItem versionMeta(UUID userId, UUID versionId) {
        ResumeVersion v = requireVersion(userId, versionId);
        return new ResumeVersionItem(v.getId(), v.getResumeId(), v.getLabel(), v.getKind(),
                v.getJobId(), v.getCreatedAt(), v.getDiff(), v.getScore());
    }

    @Transactional
    public ResumeListItem create(UUID userId, CreateResumeRequest request) {
        Resume resume = new Resume();
        resume.setUserId(userId);
        resume.setTitle(request.title().trim());
        resume.setStatus("uploaded");
        resumes.save(resume);
        ResumeVersion version = newVersion(resume, "v1", "original", null, request.plaintext());
        resume.setCurrentVersionId(version.getId());
        resumes.save(resume);
        // The second step of making a resume: the ingestion that chunks and
        // embeds it, so the agents can cite it. The upload path has its own
        // (there the file *is* the document), but a resume the reader typed
        // is text like any other -- and without this it sits in the resume
        // list and nowhere else, so the copy of the reader's own material
        // the product promises does not exist. The kind is "resume" and the
        // reference is the resume's own id: the two things deleting the
        // resume retires.
        ingestCopy(userId, resume, request.plaintext());
        return ResumeListItem.from(resume);
    }

    /**
     * The copy the agents quote: the resume's text, ingested, with the
     * resume's own id as the reference.
     *
     * <p>A failed ingestion does not cost the reader their resume: the
     * resume is theirs, the copy is derived, and the next write tries again.
     */
    private void ingestCopy(UUID userId, Resume resume, String plaintext) {
        if (plaintext == null || plaintext.isBlank()) {
            return;
        }
        try {
            knowledge.ingestText(userId, resume.getTitle(), plaintext, "resume", resume.getId());
        } catch (RuntimeException e) {
            log.warn("Ingesting the resume failed for user {}: {}", userId, e.getMessage());
        }
    }

    @Transactional
    public ResumeListItem update(UUID userId, UUID resumeId, UpdateResumeRequest request) {
        Resume resume = requireResume(userId, resumeId);
        if (request.title() != null && !request.title().isBlank()) {
            resume.setTitle(request.title().trim());
        }
        return ResumeListItem.from(resumes.save(resume));
    }

    @Transactional
    public void delete(UUID userId, UUID resumeId) {
        Resume resume = requireResume(userId, resumeId);
        // Deleting the domain row is not enough: the ingested copy stays `ready`, so the AI
        // keeps quoting a resume the user can no longer see, and the source row survives as a
        // listing entry whose target is gone.
        knowledge.retireRef(userId, "resume", resume.getId());
        resumes.delete(resume);
    }

    public UploadResumeResponse upload(UUID userId, MultipartFile file) {
        byte[] content;
        try {
            content = file.getBytes();
        } catch (java.io.IOException e) {
            throw new ApiException(ApiErrorCode.UPLOAD_UNREADABLE, "Cannot read upload");
        }
        UploadContext ctx = persistUpload(userId, content, file.getOriginalFilename());
        Map<String, Object> result;
        try {
            result = ai.ingestDocument(ctx.documentId(), userId);
        } catch (ApiException e) {
            markUploadFailed(ctx.resumeId(), e.getMessage());
            throw e;
        }
        return new UploadResumeResponse(ctx.resumeId(), ctx.versionId(), ctx.documentId(),
                ctx.sourceId(), Json.uuidOrNull(result, "task_id"));
    }

    private record UploadContext(UUID resumeId, UUID versionId, UUID documentId, UUID sourceId) {
    }

    @Transactional
    public UploadContext persistUpload(UUID userId, byte[] content, String filename) {
        FileValidator.Type type = FileValidator.validate(content);
        String ext = switch (type) {
            case PDF -> ".pdf";
            case DOCX -> ".docx";
            case TXT -> ".txt";
        };
        String key = userId + "/resumes/" + UUID.randomUUID() + ext;
        storage.put(key, content, type.mediaType());
        var persisted = fileIngest.persistRows(userId, key, type.mediaType(),
                FileIngestService.titleFrom(filename), "resume", null,
                FileIngestService.sha256(content), excerptOf(content));

        Resume resume = new Resume();
        resume.setUserId(userId);
        resume.setTitle(FileIngestService.titleFrom(filename));
        resume.setSourceFileKey(key);
        resume.setStatus("uploaded");
        resumes.save(resume);

        ResumeVersion version = newVersion(resume, "v1", "original", null, textOrNull(content));
        resume.setCurrentVersionId(version.getId());
        resumes.save(resume);

        KnowledgeSource source = sources.findById(persisted.sourceId()).orElseThrow();
        source.setRefId(resume.getId());
        sources.save(source);

        return new UploadContext(resume.getId(), version.getId(), persisted.documentId(),
                persisted.sourceId());
    }

    @Transactional
    public void markUploadFailed(UUID resumeId, String reason) {
        resumes.findById(resumeId).ifPresent(r -> {
            r.setStatus("failed");
            r.setParseError(reason == null ? "ingestion trigger failed" : reason);
        });
    }

    /**
     * The bytes behind a resume's {@code sourceFileKey}, for the detail page's "Original file"
     * affordance.
     *
     * <p>The document row is the ownership anchor, not the key: the key's first path segment embeds
     * the uploading user's id, but a key is data, and a resume row pointing at another account's key
     * would make the key check a formality. Both the resume (via {@link #requireResume}) and the
     * document row must agree the caller owns this file before a byte leaves storage. A resume
     * created by hand ({@code POST /resumes}) has no key and no row, and answers 404 rather than a
     * guess at a file.
     */
    @Transactional(readOnly = true)
    public OriginalFile originalFile(UUID userId, UUID resumeId) {
        Resume resume = requireResume(userId, resumeId);
        String key = resume.getSourceFileKey();
        if (key == null || key.isBlank()) {
            throw new ApiException(ApiErrorCode.RESUME_FILE_MISSING,
                    "This resume has no original file behind it");
        }
        Document doc = documents.findByFileKey(key)
                .filter(d -> userId.equals(d.getUserId()))
                .orElseThrow(() -> new ApiException(ApiErrorCode.RESUME_NOT_INGESTED,
                        "No ingested document owns this resume's file"));
        byte[] bytes = storage.getBytes(key);
        String name = (doc.getTitle() == null || doc.getTitle().isBlank() ? "resume" : doc.getTitle())
                + key.substring(key.lastIndexOf('.'));
        return new OriginalFile(bytes, doc.getMediaType(), name);
    }

    /** One original file download: the bytes, the stored media type, and the name to save it under. */
    public record OriginalFile(byte[] content, String mediaType, String saveName) {
    }

    public ParseResumeResponse parse(UUID userId, UUID resumeId) {
        ParsedContext ctx = parseContext(userId, resumeId);
        Map<String, Object> result = ai.parseResumeText(ctx.text(), userId);
        return persistParse(ctx.resumeId(), ctx.versionId(), userId, result, ctx.text());
    }

    private record ParsedContext(UUID resumeId, UUID versionId, String text) {
    }

    @Transactional(readOnly = true)
    public ParsedContext parseContext(UUID userId, UUID resumeId) {
        Resume resume = requireResume(userId, resumeId);
        ResumeVersion version = currentVersion(resume)
                .orElseThrow(() -> new ApiException(ApiErrorCode.RESUME_VERSION_MISSING,
                        "Resume has no version to parse"));
        String text = version.getPlaintext();
        if (text == null || text.isBlank()) {
            KnowledgeSource source = sources.findFirstByUserIdAndKindAndRefId(userId, "resume", resumeId)
                    .orElseThrow(() -> new ApiException(ApiErrorCode.RESUME_NOT_PARSED,
                            "No plaintext or ingested document for this resume"));
            Map<String, Object> doc;
            try {
                doc = ai.documentText(source.getDocumentId(), userId);
            } catch (ApiException e) {
                // The upstream answers 409 while the document is still being
                // read. That is not the assistant failing -- it is this
                // resume's text not being ready yet, which is the code this
                // service already had for it, and the sentence the reader
                // should read. Without this the upstream's answer
                // short-circuited the line below, and that code was
                // unreachable.
                if (e.code() == ApiErrorCode.AI_SERVICE_CONFLICT) {
                    throw new ApiException(ApiErrorCode.RESUME_TEXT_NOT_READY,
                            "Resume text is not available yet");
                }
                throw e;
            }
            text = Json.str(doc, "text");
        }
        if (text == null || text.isBlank()) {
            throw new ApiException(ApiErrorCode.RESUME_TEXT_NOT_READY, "Resume text is not available yet");
        }
        return new ParsedContext(resumeId, version.getId(), text);
    }

    @Transactional
    public ParseResumeResponse persistParse(UUID resumeId, UUID versionId, UUID userId,
                                            Map<String, Object> result, String plaintext) {
        Resume resume = requireResume(userId, resumeId);
        ResumeVersion version = requireVersion(userId, versionId);
        Map<String, Object> parsed = Json.obj(result.get("parsed"));
        Map<String, Object> score = Json.obj(result.get("score"));
        version.setStructured(parsed);
        if (!score.isEmpty()) {
            version.setScore(score);
        }
        if (version.getPlaintext() == null || version.getPlaintext().isBlank()) {
            // The parse answer carries {parsed, score} only, so the text has to come from the
            // caller: it is the one that was just sent, and without it the version would stay
            // blank and every later parse would re-read the document.
            version.setPlaintext(plaintext);
        }
        versions.save(version);

        populateChildren(userId, version.getId(), parsed);

        resume.setStatus("parsed");
        resume.setParseError(null);
        if (resume.getCurrentVersionId() == null) {
            resume.setCurrentVersionId(version.getId());
        }
        resumes.save(resume);

        return new ParseResumeResponse(resumeId, versionId, score,
                (int) experiences.findByResumeVersionIdOrderByOrdinalAsc(versionId).size(),
                projects.findByResumeVersionIdOrderByOrdinalAsc(versionId).size(),
                educations.findByResumeVersionIdOrderByOrdinalAsc(versionId).size(),
                achievements.findByResumeVersionIdOrderByOrdinalAsc(versionId).size(),
                resumeSkills.findByResumeVersionId(versionId).size());
    }

    @Transactional
    public ResumeListItem setVersionCurrent(UUID userId, UUID resumeId, UUID versionId) {
        Resume resume = requireResume(userId, resumeId);
        ResumeVersion version = requireVersion(userId, versionId);
        if (!version.getResumeId().equals(resumeId)) {
            throw new ApiException(ApiErrorCode.VERSION_NOT_OWNED, "Version does not belong to resume");
        }
        resume.setCurrentVersionId(versionId);
        resumes.save(resume);
        // The copy follows the current version. A reader who switches
        // versions has moved on from the text the copy carries, and an
        // assistant that keeps quoting the old one quotes a resume the
        // reader no longer has -- the same shape as a deleted note keeping
        // its chunks.
        knowledge.retireRef(userId, "resume", resumeId);
        ingestCopy(userId, resume, version.getPlaintext());
        return ResumeListItem.from(resume);
    }

    /**
     * Keeps a kept draft. The client knows the version it tailored, not the resume behind it,
     * so the resume is resolved from that version — and when the client named none (the single
     * resume case), from the same "current resume" rule the tailor call itself used.
     */
    @Transactional
    public ResumeVersionItem saveTailoredDraft(UUID userId, UUID jobId,
                                               TailoredVersionRequest request) {
        Map<String, Object> tailored = request.tailored();
        if (tailored == null || tailored.isEmpty()) {
            throw new ApiException(ApiErrorCode.VALIDATION_STRUCTURE_INVALID,
                    "A tailored version needs the structured body it was generated with");
        }
        UUID resumeId = request.resumeVersionId() != null
                ? requireVersion(userId, request.resumeVersionId()).getResumeId()
                : currentResumeWithVersion(userId).map(Resume::getId).orElse(null);
        if (resumeId == null) {
            throw new ApiException(ApiErrorCode.RESUME_NOT_AVAILABLE, "No resume available");
        }
        return saveTailoredVersion(userId, resumeId, jobId, tailored, request.diff(),
                request.plaintext());
    }

    /** Creates a tailored version for a job from ai tailor output (used by the job module). */
    @Transactional
    public ResumeVersionItem saveTailoredVersion(UUID userId, UUID resumeId, UUID jobId,
                                                 Map<String, Object> tailored,
                                                 Map<String, Object> diff, String plaintext) {
        Resume resume = requireResume(userId, resumeId);
        int next = versions.findByResumeIdAndUserIdOrderByCreatedAtDesc(resumeId, userId).size() + 1;
        // The sequence belongs in the label: the same job tailored twice must not produce two
        // rows the user cannot tell apart in the version list.
        String shortJob = jobId == null ? "" : "-" + jobId.toString().substring(0, 8);
        ResumeVersion version = newVersion(resume, "tailored" + shortJob + "-" + next, "tailored",
                jobId, plaintext);
        version.setStructured(tailored);
        version.setDiff(diff);
        versions.save(version);
        populateChildren(userId, version.getId(), tailored);
        return new ResumeVersionItem(version.getId(), version.getResumeId(), version.getLabel(),
                version.getKind(), version.getJobId(), version.getCreatedAt(), version.getDiff(),
                version.getScore());
    }

    public Optional<ResumeVersion> currentVersion(Resume resume) {
        if (resume.getCurrentVersionId() != null) {
            return versions.findById(resume.getCurrentVersionId());
        }
        return versions.findByResumeIdAndUserIdOrderByCreatedAtDesc(resume.getId(), resume.getUserId())
                .stream().findFirst();
    }

    /** Most recent resume that already has a current version (used for match/tailor defaults). */
    @Transactional(readOnly = true)
    public Optional<Resume> currentResumeWithVersion(UUID userId) {
        return resumes.findByUserIdOrderByCreatedAtDescIdAsc(userId, Paging.first(20)).getContent()
                .stream().filter(r -> r.getCurrentVersionId() != null).findFirst();
    }

    public Resume requireResume(UUID userId, UUID resumeId) {
        return resumes.findByIdAndUserId(resumeId, userId)
                .orElseThrow(() -> new ApiException(ApiErrorCode.RESUME_NOT_FOUND, "Resume not found"));
    }

    public ResumeVersion requireVersion(UUID userId, UUID versionId) {
        return versions.findByIdAndUserId(versionId, userId)
                .orElseThrow(() -> new ApiException(ApiErrorCode.VERSION_NOT_FOUND, "Resume version not found"));
    }

    private ResumeVersion newVersion(Resume resume, String label, String kind, UUID jobId,
                                     String plaintext) {
        ResumeVersion version = new ResumeVersion();
        version.setResumeId(resume.getId());
        version.setUserId(resume.getUserId());
        version.setLabel(label);
        version.setKind(kind);
        version.setJobId(jobId);
        version.setPlaintext(plaintext);
        version.setStructured(Map.of());
        return versions.save(version);
    }

    private List<SkillItem> skillItems(UUID versionId) {
        // One batched read for every skill the version's links point at: a parsed resume
        // carries dozens of skills, and a per-link findById turned the detail route into
        // the N+1 the performance checklist names first.
        List<ResumeSkill> links = resumeSkills.findByResumeVersionId(versionId);
        Map<UUID, Skill> byId = skills.findAllById(
                links.stream().map(ResumeSkill::getSkillId).toList()).stream()
                .collect(java.util.stream.Collectors.toMap(Skill::getId, s -> s));
        List<SkillItem> out = new ArrayList<>(links.size());
        for (ResumeSkill link : links) {
            Skill s = byId.get(link.getSkillId());
            if (s != null) {
                out.add(new SkillItem(s.getId(), s.getName(), s.getCategory(), link.getProficiency()));
            }
        }
        return out;
    }

    private void populateChildren(UUID userId, UUID versionId, Map<String, Object> parsed) {
        experiences.deleteByResumeVersionId(versionId);
        projects.deleteByResumeVersionId(versionId);
        educations.deleteByResumeVersionId(versionId);
        achievements.deleteByResumeVersionId(versionId);
        resumeSkills.deleteByResumeVersionId(versionId);

        int ordinal = 0;
        for (Object raw : Json.arr(parsed.get("experience"))) {
            Map<String, Object> e = Json.obj(raw);
            Experience exp = new Experience();
            exp.setResumeVersionId(versionId);
            exp.setUserId(userId);
            exp.setCompany(Json.strOr(e, "company", ""));
            exp.setTitle(Json.strOr(e, "title", ""));
            exp.setStartDate(Json.str(e, "start"));
            exp.setStartMonth(month(e.get("start")));
            exp.setEndMonth(month(e.get("end")));
            exp.setLocation(Json.str(e, "location"));
            exp.setBullets(Json.strList(e.get("bullets")));
            exp.setSummary(Json.str(e, "summary"));
            exp.setOrdinal(ordinal++);
            experiences.save(exp);
        }
        ordinal = 0;
        for (Object raw : Json.arr(parsed.get("projects"))) {
            Map<String, Object> p = Json.obj(raw);
            Project project = new Project();
            project.setResumeVersionId(versionId);
            project.setUserId(userId);
            project.setName(Json.strOr(p, "name", ""));
            project.setRole(Json.str(p, "role"));
            project.setPeriod(Json.str(p, "period"));
            project.setBullets(Json.strList(p.get("bullets")));
            project.setTech(Json.strList(p.get("tech")));
            project.setUrl(Json.str(p, "url"));
            project.setOrdinal(ordinal++);
            projects.save(project);
        }
        ordinal = 0;
        for (Object raw : Json.arr(parsed.get("education"))) {
            Map<String, Object> ed = Json.obj(raw);
            Education education = new Education();
            education.setResumeVersionId(versionId);
            education.setUserId(userId);
            education.setSchool(Json.strOr(ed, "school", ""));
            education.setDegree(Json.str(ed, "degree"));
            education.setField(Json.str(ed, "field"));
            education.setStartYear(Json.integer(ed, "startYear"));
            education.setEndYear(Json.integer(ed, "endYear"));
            education.setGpa(Json.str(ed, "gpa"));
            education.setCourses(Json.strList(ed.get("courses")));
            education.setOrdinal(ordinal++);
            educations.save(education);
        }
        ordinal = 0;
        for (Object raw : Json.arr(parsed.get("achievements"))) {
            Achievement a = new Achievement();
            a.setResumeVersionId(versionId);
            a.setUserId(userId);
            a.setText(String.valueOf(raw));
            a.setOrdinal(ordinal++);
            achievements.save(a);
        }
        for (Object raw : Json.arr(parsed.get("skills"))) {
            Map<String, Object> s = Json.obj(raw);
            String name = Json.strOr(s, "name", null);
            if (name == null || name.isBlank()) {
                continue;
            }
            Skill skill = upsertSkill(userId, name, Json.str(s, "category"));
            ResumeSkill link = new ResumeSkill();
            link.setResumeVersionId(versionId);
            link.setSkillId(skill.getId());
            link.setUserId(userId);
            Double prof = Json.dbl(s, "proficiency");
            link.setProficiency(prof == null ? null : prof.floatValue());
            resumeSkills.save(link);
        }
    }

    private Skill upsertSkill(UUID userId, String name, String category) {
        String norm = SkillNormalizer.normalize(name);
        Optional<Skill> existing = skills.findByUserIdAndNameNorm(userId, norm);
        if (existing.isPresent()) {
            Skill s = existing.get();
            s.setEvidenceCount(s.getEvidenceCount() + 1);
            if (category != null && s.getCategory() == null) {
                s.setCategory(category);
            }
            return skills.save(s);
        }
        Skill s = new Skill();
        s.setUserId(userId);
        s.setName(name.trim());
        s.setNameNorm(norm);
        s.setCategory(category == null ? "other" : category);
        s.setLevel("inferred");
        s.setEvidenceCount(1);
        return skills.save(s);
    }

    private static LocalDate month(Object value) {
        if (value == null) {
            return null;
        }
        String s = String.valueOf(value).trim();
        java.util.regex.Matcher m = java.util.regex.Pattern.compile("(\\d{4})[-/.](\\d{1,2})").matcher(s);
        if (m.find()) {
            try {
                return LocalDate.of(Integer.parseInt(m.group(1)), Integer.parseInt(m.group(2)), 1);
            } catch (RuntimeException e) {
                return null;
            }
        }
        return null;
    }

    private static String textOrNull(byte[] content) {
        if (FileValidator.validate(content) != FileValidator.Type.TXT) {
            return null;
        }
        return new String(content, java.nio.charset.StandardCharsets.UTF_8);
    }

    private static String excerptOf(byte[] content) {
        String text = textOrNull(content);
        if (text == null) {
            return null;
        }
        return Texts.truncate(text, 2000);
    }
}
