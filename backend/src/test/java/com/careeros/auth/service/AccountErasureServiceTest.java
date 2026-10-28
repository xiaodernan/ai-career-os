package com.careeros.auth.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.inOrder;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import com.careeros.auth.dto.EraseAccountRequest;
import com.careeros.auth.entity.User;
import com.careeros.auth.repository.UserRepository;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.knowledge.entity.Document;
import com.careeros.knowledge.repository.DocumentRepository;
import com.careeros.storage.StorageService;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.InOrder;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;

/**
 * Closing the account (roadmap 24.2), as far as mocks can state it.
 *
 * <p>Five claims. The typed password is re-authentication: wrong, and neither a file nor a row
 * is touched. The typed email is the deliberate half: a different account's address is refused
 * after the password passed, and case or surrounding spaces around the reader's own address are
 * forgiven. A file is deleted before the row that names it -- the order that makes a storage
 * failure leave the account whole instead of half-gone -- and a document with no key is not a
 * reason to fail. A storage failure aborts the erasure with the user row still in place. The
 * repository is read with the principal's id; the request has no field that could name another
 * account.
 *
 * <p>What mocks cannot state is that the schema really cascades. {@code AccountErasureIT} proves
 * that against the real database: the row is deleted here, and every user-scoped table is
 * expected to follow.
 */
class AccountErasureServiceTest {

    private static final UUID ALICE = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final String PASSWORD = "Str0ngPassphrase!23";
    private static final String EMAIL = "ada@example.invalid";

    private final BCryptPasswordEncoder encoder = new BCryptPasswordEncoder(4);
    private UserRepository users;
    private DocumentRepository documents;
    private StorageService storage;
    private AccountErasureService service;
    private User alice;

    @BeforeEach
    void setUp() {
        users = mock(UserRepository.class);
        documents = mock(DocumentRepository.class);
        storage = mock(StorageService.class);
        service = new AccountErasureService(users, documents, storage, encoder);

        alice = new User();
        alice.setId(ALICE);
        alice.setEmail(EMAIL);
        alice.setPasswordHash(encoder.encode(PASSWORD));
        when(users.findById(ALICE)).thenReturn(Optional.of(alice));
    }

    private static Document document(String fileKey) {
        Document document = new Document();
        document.setFileKey(fileKey);
        return document;
    }

    @Test
    void everyOwnedFileIsDeletedBeforeTheRowAndTheAddressIsReadThroughCaseAndSpaces() {
        when(documents.findByUserId(ALICE)).thenReturn(List.of(
                document(ALICE + "/notes/one.txt"),
                document(ALICE + "/resumes/two.pdf"),
                document(null),
                document("   ")));

        service.erase(ALICE, new EraseAccountRequest(PASSWORD, "  ADA@Example.INVALID  "));

        verify(documents).findByUserId(ALICE);
        InOrder order = inOrder(storage, users);
        order.verify(storage).delete(ALICE + "/notes/one.txt");
        order.verify(storage).delete(ALICE + "/resumes/two.pdf");
        order.verify(users).delete(alice);
        // A row with no key names no object; a blank key is not a path in the bucket.
        verify(storage, times(2)).delete(any());
        verify(storage, never()).delete(null);
        verify(storage, never()).delete("   ");
    }

    @Test
    void aWrongPasswordTouchesNeitherAFileNorARow() {
        assertThatThrownBy(() -> service.erase(ALICE, new EraseAccountRequest("not-the-password", EMAIL)))
                .isInstanceOfSatisfying(ApiException.class, e -> {
                    assertThat(e.code()).isEqualTo(ApiErrorCode.INVALID_CREDENTIALS);
                    assertThat(e.getMessage()).isEqualTo("Password is incorrect");
                });

        verifyNoInteractions(documents, storage);
        verify(users, never()).delete(any());
    }

    @Test
    void aTypedAddressForAnotherAccountIsRefusedAfterThePasswordPasses() {
        assertThatThrownBy(() -> service.erase(ALICE,
                new EraseAccountRequest(PASSWORD, "bob@example.invalid")))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.code()).isEqualTo(ApiErrorCode.CONFIRMATION_MISMATCH));

        verifyNoInteractions(documents, storage);
        verify(users, never()).delete(any());
    }

    @Test
    void aStorageFailureLeavesTheAccountWholeRatherThanHalfErased() {
        when(documents.findByUserId(ALICE)).thenReturn(List.of(document(ALICE + "/notes/one.txt")));
        doThrow(new ApiException(ApiErrorCode.STORAGE_DELETE_FAILED, "Object storage delete failed"))
                .when(storage).delete(ALICE + "/notes/one.txt");

        assertThatThrownBy(() -> service.erase(ALICE, new EraseAccountRequest(PASSWORD, EMAIL)))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.code()).isEqualTo(ApiErrorCode.STORAGE_DELETE_FAILED));

        verify(users, never()).delete(any());
    }

    @Test
    void anAccountThatVanishedBehindAValidTokenIsA404AndTouchesNothing() {
        when(users.findById(ALICE)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.erase(ALICE, new EraseAccountRequest(PASSWORD, EMAIL)))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.code()).isEqualTo(ApiErrorCode.USER_NOT_FOUND));

        verifyNoInteractions(documents, storage);
        verify(users, never()).delete(any());
    }
}
