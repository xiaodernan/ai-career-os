package com.careeros.knowledge.web;

import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.knowledge.entity.Document;
import com.careeros.knowledge.repository.DocumentRepository;
import com.careeros.storage.StorageService;
import jakarta.servlet.http.HttpServletRequest;
import java.util.regex.Pattern;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Service-to-service file download for ai-service ingestion (guarded by InternalApiFilter via
 * the /api/internal prefix). The key must match the upload format and belong to a documents row.
 */
@RestController
@RequestMapping("/api/internal/files")
public class InternalFileController {

    private static final Pattern FILE_KEY = Pattern.compile(
            "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
                    + "/(resumes|knowledge)/[0-9a-fA-F-]{36}\\.(pdf|docx|txt)$");

    private final DocumentRepository documents;
    private final StorageService storage;

    public InternalFileController(DocumentRepository documents, StorageService storage) {
        this.documents = documents;
        this.storage = storage;
    }

    @GetMapping("/**")
    public ResponseEntity<byte[]> get(HttpServletRequest request) {
        String prefix = request.getContextPath() + "/api/internal/files/";
        String full = request.getRequestURI();
        String fileKey = full.substring(Math.min(prefix.length(), full.length()));
        try {
            fileKey = java.net.URLDecoder.decode(fileKey, java.nio.charset.StandardCharsets.UTF_8);
        } catch (IllegalArgumentException e) {
            throw new ApiException(ApiErrorCode.BAD_REQUEST, "Malformed file key");
        }
        if (fileKey.contains("..") || fileKey.contains("\\") || !FILE_KEY.matcher(fileKey).matches()) {
            throw new ApiException(ApiErrorCode.BAD_REQUEST, "Invalid file key format");
        }
        Document doc = documents.findByFileKey(fileKey)
                .orElseThrow(() -> new ApiException(ApiErrorCode.DOCUMENT_NOT_FOUND, "No document owns this key"));
        byte[] bytes = storage.getBytes(fileKey);
        return ResponseEntity.ok()
                .contentType(MediaType.parseMediaType(doc.getMediaType()))
                .body(bytes);
    }
}
