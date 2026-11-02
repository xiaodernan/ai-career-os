package com.careeros.application.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.application.dto.ApplicationDtos.LetterItem;
import com.careeros.application.dto.ApplicationDtos.SaveLetterRequest;
import com.careeros.application.entity.Application;
import com.careeros.application.entity.ApplicationLetter;
import com.careeros.application.repository.ApplicationLetterRepository;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.test.util.ReflectionTestUtils;

/**
 * A kept letter belongs to the application it was written for: the posting and the resume
 * version come from that row, the body is trimmed, and an empty draft never becomes a row.
 */
class ApplicationLetterServiceTest {

    private final UUID userId = UUID.randomUUID();
    private final UUID applicationId = UUID.randomUUID();
    private final UUID jobId = UUID.randomUUID();
    private final UUID resumeVersionId = UUID.randomUUID();

    private ApplicationService applications;
    private ApplicationLetterRepository letters;
    private ApplicationLetterService service;

    @BeforeEach
    void setUp() {
        applications = mock(ApplicationService.class);
        letters = mock(ApplicationLetterRepository.class);
        service = new ApplicationLetterService(applications, letters);
        when(letters.save(any(ApplicationLetter.class))).thenAnswer(i -> i.getArgument(0));
    }

    private void owned() {
        Application app = new Application();
        // The id is the database's to assign, so a detached row gets the value the persistence
        // layer would have given it -- the letter is filed under the application's own id.
        ReflectionTestUtils.setField(app, "id", applicationId);
        app.setUserId(userId);
        app.setJobId(jobId);
        app.setResumeVersionId(resumeVersionId);
        when(applications.require(userId, applicationId)).thenReturn(app);
    }

    @Test
    void saveKeepsTheLetterWithThePostingAndVersionItWasWrittenFor() {
        owned();

        LetterItem item = service.save(userId, applicationId,
                new SaveLetterRequest(null, "generate", "warm", "short", "  Dear Ada,  "));

        ArgumentCaptor<ApplicationLetter> saved = ArgumentCaptor.forClass(ApplicationLetter.class);
        verify(letters).save(saved.capture());
        ApplicationLetter row = saved.getValue();
        assertThat(row.getBody()).isEqualTo("Dear Ada,");
        assertThat(row.getJobId()).isEqualTo(jobId);
        assertThat(row.getResumeVersionId()).isEqualTo(resumeVersionId);
        assertThat(row.getMode()).isEqualTo("generate");
        assertThat(row.getTone()).isEqualTo("warm");
        assertThat(row.getLength()).isEqualTo("short");
        assertThat(item.body()).isEqualTo("Dear Ada,");
    }

    @Test
    void saveRefusesAnEmptyLetterAndWritesNothing() {
        owned();

        assertThatThrownBy(() -> service.save(userId, applicationId,
                new SaveLetterRequest(null, null, null, null, "   ")))
                .isInstanceOf(ApiException.class)
                .extracting(e -> ((ApiException) e).code())
                .isEqualTo(ApiErrorCode.VALIDATION_FAILED);
        verify(letters, never()).save(any(ApplicationLetter.class));
    }

    @Test
    void listIsTheApplicationsOwnLetters() {
        owned();
        ApplicationLetter row = new ApplicationLetter();
        row.setApplicationId(applicationId);
        row.setBody("Hello");
        when(letters.findByApplicationIdAndUserIdOrderByCreatedAtDescIdDesc(applicationId, userId))
                .thenReturn(List.of(row));

        List<LetterItem> items = service.list(userId, applicationId);

        assertThat(items).hasSize(1);
        assertThat(items.get(0).body()).isEqualTo("Hello");
        verify(applications).require(userId, applicationId);
    }

    @Test
    void aLetterOnSomeoneElsesApplicationIsNotReadable() {
        when(applications.require(userId, applicationId))
                .thenThrow(new ApiException(ApiErrorCode.APPLICATION_NOT_FOUND,
                        "Application not found"));

        assertThatThrownBy(() -> service.list(userId, applicationId))
                .isInstanceOf(ApiException.class);
        verify(letters, never())
                .findByApplicationIdAndUserIdOrderByCreatedAtDescIdDesc(any(), any());
    }

    @Test
    void deleteRemovesOnlyTheApplicationsOwnLetter() {
        owned();
        UUID letterId = UUID.randomUUID();
        ApplicationLetter row = new ApplicationLetter();
        when(letters.findByIdAndApplicationIdAndUserId(letterId, applicationId, userId))
                .thenReturn(Optional.of(row));

        service.delete(userId, applicationId, letterId);

        verify(letters).delete(row);
    }

    @Test
    void deleteLeavesAnUnknownOrForeignLetterAlone() {
        owned();
        UUID letterId = UUID.randomUUID();
        when(letters.findByIdAndApplicationIdAndUserId(letterId, applicationId, userId))
                .thenReturn(Optional.empty());

        service.delete(userId, applicationId, letterId);

        verify(letters, never()).delete(any(ApplicationLetter.class));
    }
}
