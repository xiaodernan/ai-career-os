package com.careeros.auth.dto;

import java.util.List;

/**
 * The only answer that ever carries the recovery codes in clear: ten single-use codes, in
 * printed order. The database keeps hashes, so a reader who loses this answer must reissue
 * (roadmap 36.3).
 */
public record MfaActivateResponse(List<String> recoveryCodes) {
}
