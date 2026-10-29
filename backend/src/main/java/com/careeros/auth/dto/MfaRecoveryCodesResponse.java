package com.careeros.auth.dto;

import java.util.List;

/**
 * The only answer that ever carries the recovery codes in clear: ten single-use codes, in
 * printed order. Activation (36.1) and a reprint (36.3) share it, because the reader's copy of
 * the old set ends at both moments. The database keeps hashes, so a reader who loses this
 * answer must reissue.
 */
public record MfaRecoveryCodesResponse(List<String> recoveryCodes) {
}
