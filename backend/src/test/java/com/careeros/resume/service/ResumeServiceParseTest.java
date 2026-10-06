package com.careeros.resume.service;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.ai.AiServiceClient;
import com.careeros.common.ApiException;
import com.careeros.knowledge.entity.KnowledgeSource;
import com.careeros.knowledge.repository.DocumentRepository;
import com.careeros.knowledge.repository.KnowledgeSourceRepository;
import com.careeros.knowledge.service.FileIngestService;
import com.careeros.knowledge.service.KnowledgeService;
import com.careeros.resume.entity.Resume;
import com.careeros.resume.entity.ResumeVersion;
import com.careeros.resume.repository.AchievementRepository;
import com.careeros.resume.repository.EducationRepository;
import com.careeros.resume.repository.ExperienceRepository;
import com.careeros.resume.repository.ProjectRepository;
import com.careeros.resume.repository.ResumeRepository;
import com.careeros.resume.repository.ResumeSkillRepository;
import com.careeros.resume.repository.ResumeVersionRepository;
import com.careeros.resume.repository.SkillRepository;
import com.careeros.storage.StorageService;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/**
 * Parsing a resume whose text lives in an ingested document rather than in its own version row.
 *
 * The parse answer carries `{parsed, score}` and no text of its own, so the only copy of the
 * plaintext is the one `parseContext` just read out of the document. Storing that is what keeps
 * the version -- and every later parse of it -- from being empty. Ids come from Hibernate
 * (`@UuidGenerator`), so the entities are mocked to carry theirs. Plain Mockito: no DB, no Spring.
 */
class ResumeServiceParseTest {

    private final UUID userId = UUID.randomUUID();
    private final UUID resumeId = UUID.randomUUID();
    private final UUID versionId = UUID.randomUUID();
    private final UUID documentId = UUID.randomUUID();

    private ResumeRepository resumes;
    private ResumeVersionRepository versions;
    private KnowledgeSourceRepository sources;
    private AiServiceClient ai;
    private ResumeVersion version;
    private ResumeService service;

    @BeforeEach
    void setUp() {
        resumes = mock(ResumeRepository.class);
        versions = mock(ResumeVersionRepository.class);
        sources = mock(KnowledgeSourceRepository.class);
        ai = mock(AiServiceClient.class);
        service = new ResumeService(resumes, versions, mock(ExperienceRepository.class),
                mock(ProjectRepository.class), mock(EducationRepository.class),
                mock(AchievementRepository.class), mock(SkillRepository.class),
                mock(ResumeSkillRepository.class), sources, mock(KnowledgeService.class),
                mock(DocumentRepository.class), mock(FileIngestService.class),
                mock(StorageService.class), ai);
    }

    private void givenVersion(String plaintext) {
        Resume resume = mock(Resume.class);
        when(resume.getCurrentVersionId()).thenReturn(versionId);
        when(resumes.findByIdAndUserId(resumeId, userId)).thenReturn(Optional.of(resume));

        version = mock(ResumeVersion.class);
        when(version.getId()).thenReturn(versionId);
        when(version.getPlaintext()).thenReturn(plaintext);
        // parseContext resolves the *current* version through Resume.currentVersionId;
        // persistParse then re-reads it scoped to the user. Both lookups are the same row.
        when(versions.findById(versionId)).thenReturn(Optional.of(version));
        when(versions.findByIdAndUserId(versionId, userId)).thenReturn(Optional.of(version));
    }

    private void givenDocumentText(String extracted) {
        KnowledgeSource source = new KnowledgeSource();
        source.setDocumentId(documentId);
        when(sources.findFirstByUserIdAndKindAndRefId(eq(userId), eq("resume"), eq(resumeId)))
                .thenReturn(Optional.of(source));
        when(ai.documentText(documentId, userId)).thenReturn(Map.of("text", extracted));
    }

    @Test
    void storesTheTextItJustReadOutOfTheDocument() {
        String extracted = "Ada Lovelace. Analytical engine, 1843.";
        givenVersion(null);
        givenDocumentText(extracted);
        when(ai.parseResumeText(extracted, userId)).thenReturn(Map.of(
                "parsed", Map.of("profile", Map.of("name", "Ada")),
                "score", Map.of("total", 62)));

        service.parse(userId, resumeId);

        verify(version).setPlaintext(extracted);
    }

    @Test
    void aVersionThatAlreadyCarriesTextKeepsIt() {
        givenVersion("typed in by hand");
        when(ai.parseResumeText("typed in by hand", userId))
                .thenReturn(Map.of("parsed", Map.of(), "score", Map.of()));

        service.parse(userId, resumeId);

        verify(version, never()).setPlaintext(any());
        verify(ai, never()).documentText(any(), any());
    }

    @Test
    void noTextAnywhereRefusesInsteadOfParsingNothing() {
        givenVersion(" ");
        when(sources.findFirstByUserIdAndKindAndRefId(eq(userId), eq("resume"), eq(resumeId)))
                .thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.parse(userId, resumeId)).isInstanceOf(ApiException.class);

        verify(ai, never()).parseResumeText(any(), any());
        verify(version, never()).setPlaintext(any());
    }
}
