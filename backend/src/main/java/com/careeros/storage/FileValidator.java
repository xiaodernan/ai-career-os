package com.careeros.storage;

import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import java.io.InputStream;

/**
 * Content sniffing via magic bytes plus size cap for uploaded resume files
 * (pdf / docx / txt, max 20MB by default).
 */
public final class FileValidator {

    public static final long DEFAULT_MAX_BYTES = 20L * 1024 * 1024;

    public enum Type {
        PDF("application/pdf"),
        DOCX("application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        TXT("text/plain");

        private final String mediaType;

        Type(String mediaType) {
            this.mediaType = mediaType;
        }

        public String mediaType() {
            return mediaType;
        }
    }

    private FileValidator() {
    }

    /** @throws ApiException BAD_REQUEST/FILE_TOO_LARGE/INVALID_FILE_TYPE when the content is not acceptable. */
    public static Type validate(byte[] content, long maxBytes) {
        if (content == null || content.length == 0) {
            throw new ApiException(ApiErrorCode.BAD_REQUEST, "Empty file");
        }
        if (content.length > maxBytes) {
            throw new ApiException(ApiErrorCode.FILE_TOO_LARGE,
                    "File exceeds the limit of " + (maxBytes / (1024 * 1024)) + "MB");
        }
        if (startsWith(content, "%PDF".getBytes(java.nio.charset.StandardCharsets.US_ASCII))) {
            return Type.PDF;
        }
        if (startsWith(content, new byte[] {'P', 'K', 0x03, 0x04})) {
            return Type.DOCX;
        }
        if (looksLikeUtf8Text(content)) {
            return Type.TXT;
        }
        throw new ApiException(ApiErrorCode.INVALID_FILE_TYPE, "Unsupported file type (pdf/docx/txt only)");
    }

    public static Type validate(byte[] content) {
        return validate(content, DEFAULT_MAX_BYTES);
    }

    private static boolean startsWith(byte[] content, byte[] magic) {
        if (content.length < magic.length) {
            return false;
        }
        for (int i = 0; i < magic.length; i++) {
            if (content[i] != magic[i]) {
                return false;
            }
        }
        return true;
    }

    /** Strict UTF-8 decode plus control-character heuristic; rejects binaries that lack a known signature. */
    static boolean looksLikeUtf8Text(byte[] content) {
        int sample = Math.min(content.length, 8192);
        int control = 0;
        int i = 0;
        while (i < sample) {
            int b = content[i] & 0xFF;
            if (b < 0x80) {
                if (b < 0x20 && b != '\t' && b != '\n' && b != '\r') {
                    control++;
                }
                i++;
            } else {
                int extra = utf8SequenceLength(content, i, sample);
                if (extra < 0) {
                    return false;
                }
                i += extra;
            }
            if (control > sample / 20) {
                return false;
            }
        }
        return true;
    }

    /** Returns total sequence length (1..4) when a valid UTF-8 multi-byte sequence starts at offset, else -1. */
    private static int utf8SequenceLength(byte[] content, int offset, int limit) {
        int b = content[offset] & 0xFF;
        int needed;
        if ((b & 0xE0) == 0xC0) {
            needed = 2;
        } else if ((b & 0xF0) == 0xE0) {
            needed = 3;
        } else if ((b & 0xF8) == 0xF0) {
            needed = 4;
        } else {
            return -1;
        }
        if (offset + needed > limit) {
            return -1;
        }
        for (int k = 1; k < needed; k++) {
            if ((content[offset + k] & 0xC0) != 0x80) {
                return -1;
            }
        }
        return needed;
    }
}
