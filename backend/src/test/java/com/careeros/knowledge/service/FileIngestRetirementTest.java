package com.careeros.knowledge.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.careeros.ai.AiServiceClient;
import com.careeros.knowledge.entity.Document;
import com.careeros.knowledge.entity.KnowledgeSource;
import com.careeros.knowledge.repository.DocumentRepository;
import com.careeros.knowledge.repository.KnowledgeSourceRepository;
import com.careeros.storage.StorageService;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * Retirement is terminal. A late failure callback may report that an ingest did not
 * happen, but it may not un-retire the document the reader already deleted.
 */
class FileIngestRetirementTest {

    private final UUID userId = UUID.randomUUID();
    private final UUID sourceId = UUID.randomUUID();
    private final UUID documentId = UUID.randomUUID();

    private KnowledgeSourceRepository sources;
    private DocumentRepository documents;
    private FileIngestService service;

    @BeforeEach
    void setUp() {
        sources = mock(KnowledgeSourceRepository.class);
        documents = mock(DocumentRepository.class);
        service = new FileIngestService(sources, documents, mock(StorageService.class),
                mock(AiServiceClient.class), mock(TransactionTemplate.class));
    }

    @Test
    void aTriggerFailureDoesNotOverwriteTheRetirementMarker() {
        Document doc = document("retired");

        service.markFailed(new FileIngestService.Persisted(sourceId, documentId),
                "ingestion trigger failed");

        // The reader deleted the upload while the trigger was in flight; 'retired' is
        // what keeps the chunks out of retrieval, so the late failure leaves it alone.
        assertThat(doc.getStatus()).isEqualTo("retired");
        assertThat(doc.getError()).isNull();
    }

    @Test
    void aLiveDocumentStillRecordsTheTriggerFailure() {
        Document doc = document("pending");
        KnowledgeSource source = new KnowledgeSource();
        source.setStatus("ingesting");
        when(sources.findById(sourceId)).thenReturn(Optional.of(source));

        service.markFailed(new FileIngestService.Persisted(sourceId, documentId),
                "ingestion trigger failed");

        assertThat(doc.getStatus()).isEqualTo("failed");
        assertThat(doc.getError()).isEqualTo("ingestion trigger failed");
        assertThat(source.getStatus()).isEqualTo("failed");
    }

    private Document document(String status) {
        Document doc = new Document();
        doc.setUserId(userId);
        doc.setSourceId(sourceId);
        doc.setStatus(status);
        when(documents.findById(documentId)).thenReturn(Optional.of(doc));
        return doc;
    }
}
