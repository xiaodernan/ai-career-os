package com.careeros.resume.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyMap;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.ai.AiServiceClient;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
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
import com.careeros.support.TestTransactions;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

/**
 * The print read (19.5): the version's body travels to the renderer from the row,
 * never from the browser, and the answer is either a document or an error -- never
 * an empty page that looks like a rendering failure.
 */
class ResumeServicePrintTest {

    private final UUID userId = UUID.randomUUID();
    private final UUID resumeId = UUID.randomUUID();
    private final UUID versionId = UUID.randomUUID();

    private ResumeRepository resumes;
    private ResumeVersionRepository versions;
    private AiServiceClient ai;
    private ResumeService service;

    @BeforeEach
    void setUp() {
        resumes = mock(ResumeRepository.class);
        versions = mock(ResumeVersionRepository.class);
        ai = mock(AiServiceClient.class);
        service = new ResumeService(resumes, versions, mock(ExperienceRepository.class),
                mock(ProjectRepository.class), mock(EducationRepository.class),
                mock(AchievementRepository.class), mock(SkillRepository.class),
                mock(ResumeSkillRepository.class), mock(KnowledgeSourceRepository.class),
                mock(KnowledgeService.class), mock(DocumentRepository.class),
                mock(FileIngestService.class), mock(StorageService.class), ai,
                TestTransactions.executing());
    }

    private ResumeVersion givenVersionOwnedByCaller(Map<String, Object> structured,
                                                    String plaintext) {
        Resume resume = new Resume();
        ReflectionTestUtils.setField(resume, "id", resumeId);
        resume.setUserId(userId);
        resume.setTitle("Main resume");
        ResumeVersion version = new ResumeVersion();
        ReflectionTestUtils.setField(version, "id", versionId);
        version.setUserId(userId);
        version.setResumeId(resumeId);
        version.setLabel("tailored-11111111-2");
        version.setStructured(structured);
        version.setPlaintext(plaintext);
        when(versions.findByIdAndUserId(versionId, userId)).thenReturn(Optional.of(version));
        when(resumes.findByIdAndUserId(resumeId, userId)).thenReturn(Optional.of(resume));
        return version;
    }

    @Test
    void printsTheStoredBodyInTheReadersLanguage() {
        givenVersionOwnedByCaller(Map.of("profile", Map.of("name", "Ada")), "Ada, plainly");
        when(ai.renderResume(any(), anyMap(), anyString(), anyString(), anyString(), anyString()))
                .thenReturn(Map.of("format", "html", "html", "<!doctype html><h1>Ada</h1>"));

        String html = service.printHtml(userId, versionId, "zh");

        assertThat(html).isEqualTo("<!doctype html><h1>Ada</h1>");
        // The row's body, the row's plaintext and the two names the panel shows go
        // to the renderer; the locale is the reader's. Nothing comes from the caller.
        verify(ai).renderResume(userId, Map.of("profile", Map.of("name", "Ada")),
                "Ada, plainly", "Main resume", "tailored-11111111-2", "zh");
    }

    @Test
    void aVersionOfAnotherUserIsTheSameNotFoundAsAMissingOne() {
        when(versions.findByIdAndUserId(versionId, userId)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.printHtml(userId, versionId, "en"))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.code()).isEqualTo(ApiErrorCode.VERSION_NOT_FOUND));

        verify(ai, never()).renderResume(any(), anyMap(), anyString(), anyString(),
                anyString(), anyString());
    }

    @Test
    void anEmptyAnswerIsAnErrorRatherThanAnEmptyDocument() {
        // The renderer answering nothing is a failure the caller has to see; a blank
        // page behind a successful toast reads as a broken resume.
        givenVersionOwnedByCaller(Map.of(), "text");
        when(ai.renderResume(any(), anyMap(), anyString(), anyString(), anyString(), anyString()))
                .thenReturn(Map.of("format", "html"));

        assertThatThrownBy(() -> service.printHtml(userId, versionId, "en"))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.code()).isEqualTo(ApiErrorCode.AI_SERVICE_EMPTY_RESPONSE));

        when(ai.renderResume(any(), anyMap(), anyString(), anyString(), anyString(), anyString()))
                .thenReturn(Map.of("format", "html", "html", "   "));

        assertThatThrownBy(() -> service.printHtml(userId, versionId, "en"))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.code()).isEqualTo(ApiErrorCode.AI_SERVICE_EMPTY_RESPONSE));
    }
}
