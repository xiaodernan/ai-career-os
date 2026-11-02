package com.careeros.resume.service;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.inOrder;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import com.careeros.ai.AiServiceClient;
import com.careeros.knowledge.repository.DocumentRepository;
import com.careeros.knowledge.repository.KnowledgeSourceRepository;
import com.careeros.knowledge.service.FileIngestService;
import com.careeros.knowledge.service.KnowledgeService;
import com.careeros.knowledge.service.StoredObjectReclaimer;
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
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.InOrder;

/**
 * A resume upload is one object behind two rows: the resume serves the bytes as its original file
 * and the ingested copy is what the AI quotes. Deleting the resume ends both, so it is the delete
 * that reclaims; switching which version the copy carries ends only the copy, so it is not.
 */
class ResumeDeleteReclaimTest {

    private static final String KEY = "a-user/uploads/a-blob.bin";

    private final UUID userId = UUID.randomUUID();
    private final UUID resumeId = UUID.randomUUID();
    private final UUID versionId = UUID.randomUUID();

    private ResumeRepository resumes;
    private ResumeVersionRepository versions;
    private KnowledgeService knowledge;
    private StoredObjectReclaimer reclaimer;
    private ResumeService service;

    @BeforeEach
    void setUp() {
        resumes = mock(ResumeRepository.class);
        versions = mock(ResumeVersionRepository.class);
        knowledge = mock(KnowledgeService.class);
        reclaimer = mock(StoredObjectReclaimer.class);
        service = new ResumeService(resumes, versions, mock(ExperienceRepository.class),
                mock(ProjectRepository.class), mock(EducationRepository.class),
                mock(AchievementRepository.class), mock(SkillRepository.class),
                mock(ResumeSkillRepository.class), mock(KnowledgeSourceRepository.class), knowledge,
                mock(DocumentRepository.class), mock(FileIngestService.class), reclaimer,
                mock(StorageService.class), mock(AiServiceClient.class),
                TestTransactions.executing());
    }

    @Test
    void deletingAResumeReclaimsTheUploadOnlyAfterTheRowsThatNamedItAreGone() {
        Resume resume = givenResume();
        when(knowledge.retireRef(userId, "resume", resumeId)).thenReturn(List.of(KEY));

        service.delete(userId, resumeId);

        // Retirement reports the key, the row goes in the same transaction, and the reclaim is
        // handed the key only once both have happened. Waiting for the commit is the reclaimer's
        // own job (StoredObjectReclaimTest pins it); what this pins is whose delete ends the key's
        // life -- the resume's, not the version switch below.
        InOrder order = inOrder(knowledge, resumes, reclaimer);
        order.verify(knowledge).retireRef(userId, "resume", resumeId);
        order.verify(resumes).delete(resume);
        order.verify(reclaimer).reclaim(List.of(KEY));
    }

    @Test
    void aResumeWrittenByHandWithNoUploadAsksNothingOfTheStore() {
        Resume resume = givenResume();
        when(knowledge.retireRef(userId, "resume", resumeId)).thenReturn(List.of());

        service.delete(userId, resumeId);

        verify(resumes).delete(resume);
        verify(reclaimer).reclaim(List.of());
    }

    @Test
    void switchingTheCurrentVersionRetiresTheCopyAndLeavesTheUploadAlone() {
        Resume resume = givenResume();
        ResumeVersion version = mock(ResumeVersion.class);
        when(version.getId()).thenReturn(versionId);
        when(version.getResumeId()).thenReturn(resumeId);
        when(versions.findByIdAndUserId(versionId, userId)).thenReturn(Optional.of(version));
        when(knowledge.retireRef(userId, "resume", resumeId)).thenReturn(List.of(KEY));

        service.setVersionCurrent(userId, resumeId, versionId);

        // The copy the retired document carried stops being quotable, but the resume itself still
        // serves the file behind it -- so this call hands its keys to nothing.
        verifyNoInteractions(reclaimer);
        verify(resumes).save(resume);
    }

    private Resume givenResume() {
        Resume resume = mock(Resume.class);
        when(resume.getId()).thenReturn(resumeId);
        when(resumes.findByIdAndUserId(resumeId, userId)).thenReturn(Optional.of(resume));
        when(resumes.save(any(Resume.class))).thenAnswer(call -> call.getArgument(0));
        return resume;
    }
}
