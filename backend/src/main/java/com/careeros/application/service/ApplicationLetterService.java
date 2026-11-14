package com.careeros.application.service;

import com.careeros.application.dto.ApplicationDtos.LetterCatalogItem;
import com.careeros.application.dto.ApplicationDtos.LetterItem;
import com.careeros.application.dto.ApplicationDtos.SaveLetterRequest;
import com.careeros.application.dto.ApplicationDtos.UpdateLetterRequest;
import com.careeros.application.entity.Application;
import com.careeros.application.entity.ApplicationLetter;
import com.careeros.application.repository.ApplicationLetterRepository;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;
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
        ApplicationLetter row = new ApplicationLetter();
        row.setUserId(userId);
        row.setApplicationId(app.getId());
        row.setJobId(app.getJobId());
        row.setResumeVersionId(request.resumeVersionId() != null
                ? request.resumeVersionId() : app.getResumeVersionId());
        row.setMode(trimToNull(request.mode()));
        row.setTone(trimToNull(request.tone()));
        row.setLength(trimToNull(request.length()));
        row.setBody(requireBody(request.body()));
        return toItem(letters.save(row));
    }

    /**
     * Corrects a kept letter without turning it into a new row.
     *
     * <p>A reader who fixes a sentence should not have to delete the letter and keep a second
     * draft; the row's id stays, `updated_at` moves, and the drawer's order remains the moment
     * the letter was first kept. A null dial leaves the stored one alone and an empty dial clears
     * it, the same distinction the application PATCH uses for optional fields.
     */
    @Transactional
    public LetterItem update(UUID userId, UUID applicationId, UUID letterId,
                             UpdateLetterRequest request) {
        Application app = applications.require(userId, applicationId);
        ApplicationLetter row = letters.findByIdAndApplicationIdAndUserId(letterId, app.getId(), userId)
                .orElseThrow(() -> new ApiException(ApiErrorCode.APPLICATION_LETTER_NOT_FOUND,
                        "Cover letter not found"));
        row.setBody(requireBody(request.body()));
        if (request.mode() != null) {
            row.setMode(trimToNull(request.mode()));
        }
        if (request.tone() != null) {
            row.setTone(trimToNull(request.tone()));
        }
        if (request.length() != null) {
            row.setLength(trimToNull(request.length()));
        }
        // Flush before reading the row back: @UpdateTimestamp is stamped during flush, so a
        // plain save would answer the correction with the timestamp of the previous write.
        return toItem(letters.saveAndFlush(row));
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

    /**
     * Every kept letter for the caller, across all applications, newest first, capped at 200.
     * The application's title and company come along for the gallery; a letter whose application
     * row is gone stays in the answer with an empty title rather than disappearing.
     * The cap is one page the reader cannot be drowned by; the board itself users no letter-level
     * pagination because the ledger this serves was designed at letters-per-application scale.
     */
    @Transactional(readOnly = true)
    public List<LetterCatalogItem> catalog(UUID userId) {
        List<ApplicationLetter> mine = letters.findFirst200ByUserIdOrderByCreatedAtDescIdDesc(userId);
        if (mine.isEmpty()) {
            return List.of();
        }
        List<UUID> appIds = mine.stream().map(ApplicationLetter::getApplicationId).distinct().toList();
        Map<UUID, Application> titleById = applications.byIds(userId, appIds).stream()
                .collect(Collectors.toMap(Application::getId, a -> a));
        return mine.stream()
                .map(letter -> catalogItem(letter, titleById.get(letter.getApplicationId())))
                .toList();
    }

    static LetterCatalogItem catalogItem(ApplicationLetter row, Application app) {
        return new LetterCatalogItem(row.getId(), row.getApplicationId(),
                app == null ? "" : app.getTitle(),
                app == null ? "" : app.getCompanyName(),
                row.getJobId(), row.getResumeVersionId(),
                row.getMode(), row.getTone(), row.getLength(),
                row.getBody(), row.getCreatedAt(), row.getUpdatedAt());
    }

    /**
     * Removes one kept letter, if it is still there.
     *
     * <p>The delete is idempotent: a second press after a successful one answers 204 rather than
     * a 404, because the reader's intent -- "this letter should not be here" -- is already true.
     * The lookup names the application as well as the user so a letter id copied from another
     * card cannot be used to remove it through this route; a row that does not match is simply
     * not found and nothing is deleted.
     */
    @Transactional
    public void delete(UUID userId, UUID applicationId, UUID letterId) {
        Application app = applications.require(userId, applicationId);
        letters.findByIdAndApplicationIdAndUserId(letterId, app.getId(), userId)
                .ifPresent(letters::delete);
    }

    static LetterItem toItem(ApplicationLetter row) {
        return new LetterItem(row.getId(), row.getApplicationId(), row.getJobId(),
                row.getResumeVersionId(), row.getMode(), row.getTone(), row.getLength(),
                row.getBody(), row.getCreatedAt(), row.getUpdatedAt());
    }

    private static String requireBody(String value) {
        String body = value == null ? "" : value.trim();
        if (body.isEmpty()) {
            // The bean validation catches this at the HTTP edge; the service keeps the rule for
            // every caller that is not a request body (the import path writes rows directly).
            throw new ApiException(ApiErrorCode.VALIDATION_FAILED, "The letter is empty");
        }
        return body;
    }

    private static String trimToNull(String value) {
        if (value == null) {
            return null;
        }
        String trimmed = value.trim();
        return trimmed.isEmpty() ? null : trimmed;
    }
}
