package com.careeros.auth.service;

import com.careeros.auth.dto.EraseAccountRequest;
import com.careeros.auth.entity.User;
import com.careeros.auth.repository.UserRepository;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.knowledge.entity.Document;
import com.careeros.knowledge.repository.DocumentRepository;
import com.careeros.storage.StorageService;
import java.util.List;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Closing the account for good (roadmap 24.2): every row that names the reader, and every file
 * those rows point at.
 *
 * <p>The rows are already one delete. Every user-scoped table has carried
 * {@code REFERENCES users(id) ON DELETE CASCADE} since V1 -- including the two-hop
 * documents/chunks pair and the deferred link from {@code knowledge_sources} -- so removing the
 * account row empties the workspace in the same statement. The object store does not cascade: a
 * file key is a string in a bucket and no foreign key removes it, so the files named by the
 * account's document rows are deleted first and the row is removed only after every one of
 * them is gone. A storage failure therefore leaves the account whole and the request
 * retryable, never a half-erased workspace; a database failure after the files are gone leaves
 * rows whose files are gone, and the next attempt finishes what the first started -- object
 * deletion is idempotent, so neither order can double-delete into an error.
 *
 * <p>Knowledge sources are deliberately soft-retired elsewhere in the product (the file stays
 * as the audit record), which is why nothing before this service ever called
 * {@link StorageService#delete}. Erasure is the one operation where the reader's right to be
 * forgotten outranks the record: the whole point of the request is that no copy remains.
 */
@Service
public class AccountErasureService {

    private static final Logger log = LoggerFactory.getLogger(AccountErasureService.class);

    private final UserRepository users;
    private final DocumentRepository documents;
    private final StorageService storage;
    private final PasswordEncoder passwordEncoder;

    public AccountErasureService(UserRepository users, DocumentRepository documents,
                                 StorageService storage, PasswordEncoder passwordEncoder) {
        this.users = users;
        this.documents = documents;
        this.storage = storage;
        this.passwordEncoder = passwordEncoder;
    }

    /**
     * Re-authenticates twice, removes the files the account owns and then the account itself.
     * The password is the barrier; the typed address is the deliberate half, so the destructive
     * button takes a second, explicit act rather than one click. It is compared without case
     * or surrounding spaces -- a reader who copies their own address off the screen should not
     * be failed by their keyboard -- while a value for a different account must not pass.
     */
    @Transactional
    public void erase(UUID userId, EraseAccountRequest request) {
        User user = users.findById(userId)
                .orElseThrow(() -> new ApiException(ApiErrorCode.USER_NOT_FOUND, "User not found"));
        if (!passwordEncoder.matches(request.password(), user.getPasswordHash())) {
            throw new ApiException(ApiErrorCode.CURRENT_PASSWORD_INCORRECT,
                    "Current password is incorrect");
        }
        if (!user.getEmail().equalsIgnoreCase(request.confirmEmail().trim())) {
            throw new ApiException(ApiErrorCode.CONFIRMATION_MISMATCH,
                    "The typed email does not match this account");
        }

        List<Document> owned = documents.findByUserId(userId);
        for (Document document : owned) {
            String key = document.getFileKey();
            if (key != null && !key.isBlank()) {
                storage.delete(key);
            }
        }
        users.delete(user);
        log.info("Account erased for user {}", userId);
    }
}
