package com.careeros.storage;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import org.junit.jupiter.api.Test;

class FileValidatorTest {

    @Test
    void detectsPdfByMagicBytes() {
        byte[] content = concat(new byte[] {'%', 'P', 'D', 'F', '-', '1', '.', '7', '\n',
                (byte) 0xE2, (byte) 0xE3, (byte) 0xCF, (byte) 0xD3}, 64);
        assertEquals(FileValidator.Type.PDF, FileValidator.validate(content));
    }

    @Test
    void detectsDocxByZipSignature() {
        byte[] content = concat(new byte[] {'P', 'K', 0x03, 0x04, 0x14, 0x00}, 128);
        assertEquals(FileValidator.Type.DOCX, FileValidator.validate(content));
    }

    @Test
    void acceptsUtf8PlainTextIncludingMultibyte() {
        byte[] content = "简历 — resume with €uro and ✓ marks\n".repeat(10).getBytes(StandardCharsets.UTF_8);
        assertEquals(FileValidator.Type.TXT, FileValidator.validate(content));
    }

    @Test
    void rejectsExecutableBinary() {
        byte[] content = new byte[512];
        content[0] = 0x7F;
        content[1] = 'E';
        content[2] = 'L';
        content[3] = 'F';
        for (int i = 4; i < content.length; i++) {
            content[i] = (byte) (i % 251); // dense non-text control/binary bytes
        }
        ApiException ex = assertThrows(ApiException.class, () -> FileValidator.validate(content));
        assertEquals(ApiErrorCode.INVALID_FILE_TYPE, ex.code());
    }

    @Test
    void rejectsInvalidUtf8Sequence() {
        byte[] broken = new byte[] {'h', 'i', (byte) 0xC3, 0x28, 'x'}; // invalid continuation byte
        assertThrows(ApiException.class, () -> FileValidator.validate(broken));
    }

    @Test
    void rejectsEmptyFile() {
        ApiException ex = assertThrows(ApiException.class, () -> FileValidator.validate(new byte[0]));
        assertEquals(ApiErrorCode.BAD_REQUEST, ex.code());
    }

    @Test
    void rejectsOversizedFile() {
        byte[] big = new byte[(int) (1024 * 1024)];
        big[0] = '%';
        big[1] = 'P';
        big[2] = 'D';
        big[3] = 'F';
        ApiException ex = assertThrows(ApiException.class, () -> FileValidator.validate(big, 1024));
        assertEquals(ApiErrorCode.FILE_TOO_LARGE, ex.code());
    }

    private static byte[] concat(byte[] head, int totalLength) {
        return Arrays.copyOf(head, totalLength);
    }
}
