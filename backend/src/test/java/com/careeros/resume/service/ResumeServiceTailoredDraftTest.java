package com.careeros.resume.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.atLeastOnce;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.ai.AiServiceClient;
import com.careeros.common.ApiException;
import com.careeros.knowledge.repository.DocumentRepository;
import com.careeros.knowledge.repository.KnowledgeSourceRepository;
import com.careeros.knowledge.service.FileIngestService;
import com.careeros.knowledge.service.KnowledgeService;
import com.careeros.resume.dto.ResumeDtos.ResumeVersionItem;
import com.careeros.resume.dto.ResumeDtos.TailoredVersionRequest;
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
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.data.domain.PageImpl;

/**
 * Keeping a tailored draft: the version must land on the resume the draft was generated from,
 * and never on someone else's. Plain Mockito — no DB, no Spring context.
 */
class ResumeServiceTailoredDraftTest {

    private final UUID userId = UUID.randomUUID();
    private final UUID resumeId = UUID.randomUUID();
    private final UUID baseVersionId = UUID.randomUUID();
    private final UUID jobId = UUID.fromString("11111111-2222-3333-4444-555555555555");

    private ResumeRepository resumes;
    private ResumeVersionRepository versions;
    private ResumeService service;

    @BeforeEach
    void setUp() {
        resumes = mock(ResumeRepository.class);
        versions = mock(ResumeVersionRepository.class);
        service = new ResumeService(resumes, versions, mock(ExperienceRepository.class),
                mock(ProjectRepository.class), mock(EducationRepository.class),
                mock(AchievementRepository.class), mock(SkillRepository.class),
                mock(ResumeSkillRepository.class), mock(KnowledgeSourceRepository.class),
                mock(KnowledgeService.class), mock(DocumentRepository.class),
                mock(FileIngestService.class), mock(StorageService.class),
                mock(AiServiceClient.class), TestTransactions.executing());
        when(versions.save(any(ResumeVersion.class))).thenAnswer(i -> i.getArgument(0));
    }

    private void givenBaseVersionOnOwnResume() {
        ResumeVersion base = new ResumeVersion();
        base.setUserId(userId);
        base.setResumeId(resumeId);
        when(versions.findByIdAndUserId(baseVersionId, userId)).thenReturn(Optional.of(base));
        when(resumes.findByIdAndUserId(resumeId, userId)).thenReturn(Optional.of(new Resume()));
    }

    private ResumeVersion saved() {
        // newVersion() persists, then the caller fills structured/diff and saves the same
        // managed instance again — one INSERT at flush, two calls to the mock.
        ArgumentCaptor<ResumeVersion> cap = ArgumentCaptor.forClass(ResumeVersion.class);
        verify(versions, atLeastOnce()).save(cap.capture());
        List<ResumeVersion> all = cap.getAllValues();
        return all.get(all.size() - 1);
    }

    private TailoredVersionRequest request(Map<String, Object> tailored) {
        return new TailoredVersionRequest(baseVersionId, tailored,
                Map.of("accepted", List.of("rewrote bullets")), "Assembled document");
    }

    @Test
    void keepsTheDraftOnTheResumeTheBaseVersionBelongsTo() {
        givenBaseVersionOnOwnResume();

        service.saveTailoredDraft(userId, jobId, request(Map.of("profile", Map.of("name", "Ada"))));

        // the resume is resolved through the base version, not trusted from the client
        verify(resumes).findByIdAndUserId(eq(resumeId), eq(userId));
        ResumeVersion v = saved();
        assertThat(v.getKind()).isEqualTo("tailored");
        assertThat(v.getJobId()).isEqualTo(jobId);
        assertThat(v.getPlaintext()).isEqualTo("Assembled document");
        assertThat(v.getDiff()).isEqualTo(Map.of("accepted", List.of("rewrote bullets")));
        assertThat(v.getStructured()).containsKey("profile");
    }

    @Test
    void theReturnedItemCarriesTheLabelAndKindThePanelRenders() {
        givenBaseVersionOnOwnResume();
        when(versions.findByResumeIdAndUserIdOrderByCreatedAtDesc(resumeId, userId))
                .thenReturn(List.of());

        ResumeVersionItem item =
                service.saveTailoredDraft(userId, jobId, request(Map.of("profile", Map.of())));

        assertThat(item.kind()).isEqualTo("tailored");
        assertThat(item.label()).isEqualTo("tailored-11111111-1");
        assertThat(item.jobId()).isEqualTo(jobId);
    }

    @Test
    void aSecondDraftForTheSameJobGetsItsOwnLabel() {
        givenBaseVersionOnOwnResume();
        when(versions.findByResumeIdAndUserIdOrderByCreatedAtDesc(resumeId, userId))
                .thenReturn(List.of(new ResumeVersion(), new ResumeVersion()));

        ResumeVersionItem item =
                service.saveTailoredDraft(userId, jobId, request(Map.of("profile", Map.of())));

        // two rows both called "tailored-<jobId>" are indistinguishable in the version list
        assertThat(item.label()).isEqualTo("tailored-11111111-3");
    }

    @Test
    void refusesToStoreAnEmptyBody() {
        assertThatThrownBy(() -> service.saveTailoredDraft(userId, jobId, request(Map.of())))
                .isInstanceOf(ApiException.class)
                .hasMessageContaining("structured body");
        assertThatThrownBy(() -> service.saveTailoredDraft(userId, jobId, request(null)))
                .isInstanceOf(ApiException.class);

        verify(versions, never()).save(any(ResumeVersion.class));
        verify(resumes, never()).findByIdAndUserId(any(), any());
    }

    @Test
    void someoneElsesBaseVersionIsNotFoundNotSaved() {
        when(versions.findByIdAndUserId(baseVersionId, userId)).thenReturn(Optional.empty());

        assertThatThrownBy(() ->
                service.saveTailoredDraft(userId, jobId, request(Map.of("profile", Map.of()))))
                .isInstanceOf(ApiException.class);

        verify(versions, never()).save(any(ResumeVersion.class));
    }

    @Test
    void noBaseVersionFallsBackToTheCurrentResumeLikeTheTailorCallDoes() {
        // Resume's id comes from the database (@UuidGenerator), so the entity is mocked to
        // carry one — the point of the test is which resume the draft is filed under.
        Resume current = mock(Resume.class);
        when(current.getId()).thenReturn(resumeId);
        when(current.getCurrentVersionId()).thenReturn(baseVersionId);
        when(resumes.findByUserIdOrderByCreatedAtDescIdAsc(eq(userId), any()))
                .thenReturn(new PageImpl<>(List.of(current)));
        when(resumes.findByIdAndUserId(any(), eq(userId))).thenReturn(Optional.of(new Resume()));

        service.saveTailoredDraft(userId, jobId,
                new TailoredVersionRequest(null, Map.of("profile", Map.of()), null, null));

        verify(resumes).findByUserIdOrderByCreatedAtDescIdAsc(eq(userId), any());
        verify(versions, never()).findByIdAndUserId(any(), any());
        verify(versions, atLeastOnce()).save(any(ResumeVersion.class));
    }

    @Test
    void noResumeAtAllIsANotFoundNotAnEmptyVersion() {
        when(resumes.findByUserIdOrderByCreatedAtDescIdAsc(eq(userId), any()))
                .thenReturn(new PageImpl<>(List.of()));

        assertThatThrownBy(() -> service.saveTailoredDraft(userId, jobId,
                new TailoredVersionRequest(null, Map.of("profile", Map.of()), null, null)))
                .isInstanceOf(ApiException.class);

        verify(versions, never()).save(any(ResumeVersion.class));
    }
}
