package com.careeros.knowledge.service;

import com.careeros.ai.AiServiceClient;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.common.Json;
import com.careeros.common.Texts;
import com.careeros.knowledge.entity.Document;
import com.careeros.knowledge.entity.KnowledgeSource;
import com.careeros.knowledge.repository.DocumentRepository;
import com.careeros.knowledge.repository.KnowledgeSourceRepository;
import com.careeros.storage.FileValidator;
import com.careeros.storage.StorageService;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * Registers uploads: validates bytes, stores in object storage, inserts knowledge_sources +
 * documents rows, then triggers ai-service ingestion outside the row-creating transaction so
 * rows survive an AI outage (status is marked failed instead).
 */
@Service
public class FileIngestService {

    public record Persisted(UUID sourceId, UUID documentId) {
    }

    private final KnowledgeSourceRepository sources;
    private final DocumentRepository documents;
    private final StorageService storage;
    private final AiServiceClient ai;
    private final TransactionTemplate tx;

    public FileIngestService(KnowledgeSourceRepository sources, DocumentRepository documents,
                             StorageService storage, AiServiceClient ai, TransactionTemplate tx) {
        this.sources = sources;
        this.documents = documents;
        this.storage = storage;
        this.ai = ai;
        this.tx = tx;
    }

    public Persisted uploadAndIngest(UUID userId, byte[] content, String filename, String kind,
                                     String folder, UUID refId) {
        FileValidator.Type type = FileValidator.validate(content);
        String key = keyFor(userId, folder, type);
        storage.put(key, content, type.mediaType());
        String title = titleFrom(filename);
        // The three rows are one batch: a source titled like a finished upload with no document
        // behind it never leaves "ingesting", never becomes citable, and is counted by the list.
        // The annotation on persistRows cannot arm a call this object makes on itself, so this
        // method opens the transaction instead and leaves the model call below outside it -- which
        // is what the class javadoc has always promised. FileIngestAtomicityIT holds both halves.
        Persisted persisted = tx.execute(status -> persistRows(userId, key, type.mediaType(), title,
                kind, refId, sha256(content), excerptFor(type, content)));
        try {
            ai.ingestDocument(persisted.documentId(), userId);
        } catch (ApiException e) {
            markFailed(persisted, "ingestion trigger failed");
            throw e;
        }
        return persisted;
    }

    public Persisted persistRowsOnly(UUID userId, byte[] content, String title, String kind,
                                     String folder) {
        FileValidator.Type type = FileValidator.validate(content);
        String key = keyFor(userId, folder, type);
        storage.put(key, content, type.mediaType());
        String effectiveTitle = title == null || title.isBlank() ? titleFrom(null) : title;
        // The live upload route's batch, armed the same way: see uploadAndIngest.
        return tx.execute(status -> persistRows(userId, key, type.mediaType(), effectiveTitle, kind,
                null, sha256(content), excerptFor(type, content)));
    }

    public Map<String, Object> triggerIngest(Persisted persisted, UUID userId) {
        return ai.ingestDocument(persisted.documentId(), userId);
    }

    private static String keyFor(UUID userId, String folder, FileValidator.Type type) {
        String ext = switch (type) {
            case PDF -> "pdf";
            case DOCX -> "docx";
            case TXT -> "txt";
        };
        return userId + "/" + folder + "/" + UUID.randomUUID() + "." + ext;
    }

    @Transactional
    public Persisted persistRows(UUID userId, String fileKey, String mediaType, String title,
                                 String kind, UUID refId, String contentHash, String excerpt) {
        KnowledgeSource source = new KnowledgeSource();
        source.setUserId(userId);
        source.setKind(kind);
        source.setRefId(refId);
        source.setTitle(title);
        source.setStatus("ingesting");
        sources.save(source);

        Document doc = new Document();
        doc.setUserId(userId);
        doc.setSourceId(source.getId());
        doc.setFileKey(fileKey);
        doc.setMediaType(mediaType);
        doc.setTitle(title);
        doc.setContentHash(contentHash);
        doc.setTextExcerpt(excerpt);
        doc.setMeta(Map.of("kind", kind));
        doc.setStatus("pending");
        documents.save(doc);

        source.setDocumentId(doc.getId());
        sources.save(source);
        return new Persisted(source.getId(), doc.getId());
    }

    @Transactional
    public void markFailed(Persisted persisted, String reason) {
        sources.findById(persisted.sourceId()).ifPresent(s -> {
            s.setStatus("failed");
            s.setError(reason);
        });
        documents.findById(persisted.documentId()).ifPresent(d -> {
            d.setStatus("failed");
            d.setError(reason);
        });
    }

    /** Inline-text ingestion: ai-service itself creates source+document rows for /internal/ingest/text. */
    public Map<String, Object> ingestText(UUID userId, String title, String text, String kind, UUID refId) {
        return ai.ingestText(userId, title, text, kind, refId);
    }

    public static String titleFrom(String filename) {
        if (filename == null || filename.isBlank()) {
            return "Untitled";
        }
        String base = filename.replace('\\', '/');
        base = base.substring(base.lastIndexOf('/') + 1);
        int dot = base.lastIndexOf('.');
        if (dot > 0) {
            base = base.substring(0, dot);
        }
        return base.isBlank() ? "Untitled" : Texts.truncate(base, 200);
    }

    public static String sha256(byte[] content) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return HexFormat.of().formatHex(digest.digest(content));
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }

    private static String excerptFor(FileValidator.Type type, byte[] content) {
        if (type != FileValidator.Type.TXT) {
            return null;
        }
        String text = new String(content, StandardCharsets.UTF_8);
        return Texts.truncate(text, 2000);
    }

    public Document requireDocument(UUID userId, UUID documentId) {
        return documents.findById(documentId)
                .filter(d -> d.getUserId().equals(userId))
                .orElseThrow(() -> new ApiException(ApiErrorCode.DOCUMENT_NOT_FOUND, "Document not found"));
    }
}
