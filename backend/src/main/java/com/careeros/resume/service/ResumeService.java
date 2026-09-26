package com.careeros.resume.service;

import com.careeros.ai.AiServiceClient;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.common.Json;
import com.careeros.common.PageDTO;
import com.careeros.common.Paging;
import com.careeros.common.Texts;
import com.careeros.knowledge.entity.KnowledgeSource;
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
    private final KnowledgeService knowledge;
    private final FileIngestService fileIngest;
    private final StorageService storage;
    private final AiServiceClient ai;

    public ResumeService(ResumeRepository resumes, ResumeVersionRepository versions,
                         ExperienceRepository experiences, ProjectRepository projects,
                         EducationRepository educations, AchievementRepository achievements,
                         SkillRepository skills, ResumeSkillRepository resumeSkills,
                         KnowledgeSourceRepository sources, KnowledgeService knowledge,
                         FileIngestService fileIngest,
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
        this.knowledge = knowledge;
        this.fileIngest = fileIngest;
        this.storage = storage;
        this.ai = ai;
    }

    @Transactional(readOnly = true)
    public PageDTO<ResumeListItem> list(UUID userId, Pageable pageable) {
        var page = resumes.findByUserIdOrderByCreatedAtDesc(userId, pageable);
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
        return ResumeListItem.from(resume);
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
            throw new ApiException(ApiErrorCode.BAD_REQUEST, "Cannot read upload");
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
                .orElseThrow(() -> new ApiException(ApiErrorCode.VERSION_NOT_FOUND,
                        "Resume has no version to parse"));
        String text = version.getPlaintext();
        if (text == null || text.isBlank()) {
            KnowledgeSource source = sources.findFirstByUserIdAndKindAndRefId(userId, "resume", resumeId)
                    .orElseThrow(() -> new ApiException(ApiErrorCode.DOCUMENT_NOT_FOUND,
                            "No plaintext or ingested document for this resume"));
            Map<String, Object> doc = ai.documentText(source.getDocumentId(), userId);
            text = Json.str(doc, "text");
        }
        if (text == null || text.isBlank()) {
            throw new ApiException(ApiErrorCode.BAD_REQUEST, "Document text is not available yet");
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
            throw new ApiException(ApiErrorCode.VERSION_NOT_FOUND, "Version does not belong to resume");
        }
        resume.setCurrentVersionId(versionId);
        return ResumeListItem.from(resumes.save(resume));
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
            throw new ApiException(ApiErrorCode.VALIDATION_FAILED,
                    "A tailored version needs the structured body it was generated with");
        }
        UUID resumeId = request.resumeVersionId() != null
                ? requireVersion(userId, request.resumeVersionId()).getResumeId()
                : currentResumeWithVersion(userId).map(Resume::getId).orElse(null);
        if (resumeId == null) {
            throw new ApiException(ApiErrorCode.RESUME_NOT_FOUND, "No resume available");
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
        return resumes.findByUserIdOrderByCreatedAtDesc(userId, Paging.first(20)).getContent()
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
        List<SkillItem> out = new ArrayList<>();
        for (ResumeSkill link : resumeSkills.findByResumeVersionId(versionId)) {
            skills.findById(link.getSkillId()).ifPresent(s -> out.add(
                    new SkillItem(s.getId(), s.getName(), s.getCategory(), link.getProficiency())));
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
