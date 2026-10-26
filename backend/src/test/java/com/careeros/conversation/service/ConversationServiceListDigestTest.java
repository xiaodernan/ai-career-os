package com.careeros.conversation.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.ai.AiServiceClient;
import com.careeros.common.PageDTO;
import com.careeros.conversation.dto.ConversationDtos.ConversationItem;
import com.careeros.conversation.entity.Conversation;
import com.careeros.conversation.repository.ConversationDigestRepository;
import com.careeros.conversation.repository.ConversationDigestRepository.Digest;
import com.careeros.conversation.repository.ConversationRepository;
import com.careeros.conversation.repository.MessageRepository;
import com.careeros.support.TestTransactions;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;

/**
 * The sidebar row has to say what a chat last said and how long it got. Both are aggregates over
 * `messages`, so the page fetches them in one batched lookup — and a chat with no thread shows
 * nothing rather than a fabricated empty preview.
 */
class ConversationServiceListDigestTest {

    private final UUID userId = UUID.randomUUID();
    private final UUID first = UUID.randomUUID();
    private final UUID second = UUID.randomUUID();

    private ConversationRepository conversations;
    private ConversationDigestRepository digests;
    private ConversationService service;

    @BeforeEach
    void setUp() {
        conversations = mock(ConversationRepository.class);
        digests = mock(ConversationDigestRepository.class);
        service = new ConversationService(conversations, mock(MessageRepository.class), digests,
                mock(AiServiceClient.class), TestTransactions.executing());
    }

    /** Ids come from the database, so the entity is mocked to carry one. */
    private Conversation chat(UUID id, String title) {
        Conversation c = mock(Conversation.class);
        when(c.getId()).thenReturn(id);
        when(c.getTitle()).thenReturn(title);
        return c;
    }

    private void givenPage(Conversation... rows) {
        when(conversations.findByUserIdOrderByUpdatedAtDescIdAsc(any(), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(rows), PageRequest.of(0, 50), rows.length));
    }

    private List<ConversationItem> listed() {
        PageDTO<ConversationItem> page = service.list(userId, 0, 50);
        return page.items();
    }

    @Test
    void theRowCarriesTheLastMessageAndTheCount() {
        givenPage(chat(first, "RAG question"), chat(second, "Salary talk"));
        when(digests.forConversations(any())).thenReturn(Map.of(
                first, new Digest("You could chunk by heading", 8),
                second, new Digest(null, 0)));

        List<ConversationItem> items = listed();

        assertThat(items.get(0).lastMessagePreview()).isEqualTo("You could chunk by heading");
        assertThat(items.get(0).messageCount()).isEqualTo(8);
        // an empty chat has said nothing: a dash renders as "no preview", "" would read as content
        assertThat(items.get(1).lastMessagePreview()).isNull();
        assertThat(items.get(1).messageCount()).isZero();
    }

    @Test
    void theAggregatesAreFetchedOnceForTheWholePage() {
        givenPage(chat(first, "A"), chat(second, "B"));
        when(digests.forConversations(any())).thenReturn(Map.of());

        listed();

        ArgumentCaptor<Collection<UUID>> cap = ArgumentCaptor.forClass(Collection.class);
        verify(digests).forConversations(cap.capture());
        assertThat(cap.getValue()).containsExactlyInAnyOrder(first, second);
    }

    @Test
    void aConversationMissingFromTheDigestMapReportsNoCountRatherThanAFakeOne() {
        givenPage(chat(first, "A"));
        // the page asked for one row and the batch answered for none of them
        when(digests.forConversations(any())).thenReturn(Map.of());

        List<ConversationItem> items = listed();

        assertThat(items.get(0).messageCount()).isNull();
        assertThat(items.get(0).lastMessagePreview()).isNull();
    }

    @Test
    void singleRowReadsDoNotInventAggregates() {
        ConversationItem item = ConversationService.toItem(chat(first, "RAG question"));

        // detail/create/update responses load no thread; claiming 0 messages there would be as
        // wrong as claiming the real number
        assertThat(item.messageCount()).isNull();
        assertThat(item.lastMessagePreview()).isNull();
        assertThat(item.title()).isEqualTo("RAG question");
    }

    @Test
    void aMarkdownAnswerFoldsOntoTheSingleLineTheSidebarHas() {
        // the preview sits in a `truncate` <p>: a leading newline would collapse into a gap that
        // looks like a rendering bug, and internal ones would eat the rest of the line.
        String preview = ConversationService.excerpt("## Summary\n\n  use pgvector,\n  then rerank  ");

        assertThat(preview).isEqualTo("## Summary use pgvector, then rerank");
    }

    @Test
    void aBlankStoredMessageYieldsNoPreviewNotNullSentinel() {
        assertThat(ConversationService.excerpt(null)).isNull();
        assertThat(ConversationService.excerpt("   \n\t ")).isNull();
    }

    @Test
    void thePreviewIsCappedWithoutSplittingASurrogatePair() {
        String message = "a".repeat(59) + "\uD83D\uDE00 rest of a long answer that keeps going";

        String preview = ConversationService.excerpt(message);

        assertThat(preview).endsWith("…");
        String kept = preview.substring(0, preview.length() - 1);
        assertThat(Character.isHighSurrogate(kept.charAt(kept.length() - 1))).isFalse();
        assertThat(kept).hasSizeLessThanOrEqualTo(60);
    }
}
