package com.careeros.application.service;

import com.careeros.application.dto.ApplicationDtos.LetterItem;
import com.careeros.application.dto.ApplicationDtos.SaveLetterRequest;
import com.careeros.application.entity.Application;
import com.careeros.application.entity.ApplicationLetter;
import com.careeros.application.repository.ApplicationLetterRepository;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * The cover letters an application keeps.
 *
 * <p>A letter used to be a relay: the job page asked the ai-service for a draft and handed the
 * text to the browser, so closing the tab was the only save there was. This service is the place
 * a draft is kept, and every read and write is scoped by the application's owner -- a letter is
 * as private as the application it belongs to.
 */
@Service
public class ApplicationLetterService {

    private final ApplicationService applications;
    private final ApplicationLetterRepository letters;

    public ApplicationLetterService(ApplicationService applications,
                                    ApplicationLetterRepository letters) {
        this.applications = applications;
        this.letters = letters;
    }

    @Transactional
    public LetterItem save(UUID userId, UUID applicationId, SaveLetterRequest request) {
        Application app = applications.require(userId, applicationId);
        String body = request.body() == null ? "" : request.body().trim();
        if (body.isEmpty()) {
            // The bean validation catches this at the HTTP edge; the service keeps the rule for
            // every caller that is not a request body (the import path writes rows directly).
            throw new ApiException(ApiErrorCode.VALIDATION_FAILED, "The letter is empty");
        }
        ApplicationLetter row = new ApplicationLetter();
        row.setUserId(userId);
        row.setApplicationId(app.getId());
        row.setJobId(app.getJobId());
        row.setResumeVersionId(request.resumeVersionId() != null
                ? request.resumeVersionId() : app.getResumeVersionId());
        row.setMode(trimToNull(request.mode()));
        row.setTone(trimToNull(request.tone()));
        row.setLength(trimToNull(request.length()));
        row.setBody(body);
        return toItem(letters.save(row));
    }

    /** Newest first: a regenerated letter is the one the reader is looking at. */
    @Transactional(readOnly = true)
    public List<LetterItem> list(UUID userId, UUID applicationId) {
        Application app = applications.require(userId, applicationId);
        return letters.findByApplicationIdAndUserIdOrderByCreatedAtDescIdDesc(app.getId(), userId)
                .stream()
                .map(ApplicationLetterService::toItem)
                .toList();
    }

    static LetterItem toItem(ApplicationLetter row) {
        return new LetterItem(row.getId(), row.getApplicationId(), row.getJobId(),
                row.getResumeVersionId(), row.getMode(), row.getTone(), row.getLength(),
                row.getBody(), row.getCreatedAt());
    }

    private static String trimToNull(String value) {
        if (value == null) {
            return null;
        }
        String trimmed = value.trim();
        return trimmed.isEmpty() ? null : trimmed;
    }
}
